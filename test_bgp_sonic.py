"""
SONiC BGP Session Status Tests
Validates BGP neighbor states by connecting to the SONiC device over SSH
and running `vtysh -c "show bgp summary json"`.

Requirements:
    pip install pytest paramiko

Run:
    pytest test_bgp_sonic.py -v
"""

import json
import pytest
import paramiko


# ===========================================================================
# CONFIGURATION — edit these variables before running
# ===========================================================================

DEVICE_IP       = "172.80.80.11"   # IP address of the SONiC device
SSH_USERNAME    = "admin"          # SSH username
SSH_PASSWORD    = "admin"          # SSH password
SSH_PORT        = 22               # SSH port (default: 22)
SSH_TIMEOUT     = 15               # Connection timeout in seconds

BGP_NEIGHBOR_1  = "192.168.11.1"  # First BGP neighbor to check
BGP_NEIGHBOR_2  = "10.0.2.1"      # Second BGP neighbor to check

# ===========================================================================


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ssh_run_command(command: str) -> str:
    """
    Opens an SSH connection to the SONiC device, runs the given command,
    and returns stdout as a string. Raises on non-zero exit code.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=DEVICE_IP,
            port=SSH_PORT,
            username=SSH_USERNAME,
            password=SSH_PASSWORD,
            timeout=SSH_TIMEOUT,
            look_for_keys=False,
            allow_agent=False,
        )
        stdin, stdout, stderr = client.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        err = stderr.read().decode()
        if exit_code != 0:
            raise RuntimeError(
                f"Command '{command}' exited with code {exit_code}.\n"
                f"STDERR: {err}\nSTDOUT: {out}"
            )
        return out
    finally:
        client.close()


def get_bgp_summary() -> dict:
    """
    Returns the parsed JSON output of `show bgp summary` retrieved via SSH.
    FRR structure: { "ipv4Unicast": { "peers": { "<ip>": { "state": "..." } } }, ... }
    """
    raw = ssh_run_command("vtysh -c 'show bgp summary json'")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        pytest.fail(f"Could not parse BGP summary JSON: {exc}\nRaw output:\n{raw}")


def get_peer_state(bgp_summary: dict, neighbor_ip: str) -> str | None:
    """
    Search all address-families for the given neighbor and return its BGP state.
    Returns None if the neighbor is not found in any address-family.
    """
    for af_data in bgp_summary.values():
        if not isinstance(af_data, dict):
            continue
        peers = af_data.get("peers", {})
        if neighbor_ip in peers:
            return peers[neighbor_ip].get("state", "Unknown")
    return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def bgp_summary():
    """Fetch BGP summary once over SSH for the entire test module."""
    return get_bgp_summary()


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

EXPECTED_STATE = "Established"

@pytest.mark.parametrize("neighbor_ip", [
    BGP_NEIGHBOR_1,
    BGP_NEIGHBOR_2,
])
def test_bgp_neighbor_established(bgp_summary, neighbor_ip):
    """
    Verify that the BGP session with each expected neighbor is in
    the 'Established' state.
    """
    state = get_peer_state(bgp_summary, neighbor_ip)

    print(f"\n BGP neighbour = {neighbor_ip} , State = {state if state is not None else 'NOT FOUND'}")

    assert state is not None, (
        f"Neighbor {neighbor_ip} was NOT found in the BGP summary. "
        "Check that the neighbor is configured and the correct VRF is used."
    )
    assert state == EXPECTED_STATE, (
        f"BGP neighbor {neighbor_ip} is in state '{state}', expected '{EXPECTED_STATE}'."
    )
