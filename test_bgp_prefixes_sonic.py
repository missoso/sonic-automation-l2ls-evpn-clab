"""
SONiC BGP L2VPN EVPN Prefix Sent/Received Test
Connects to a SONiC device over SSH and reports the number of EVPN prefixes
sent and received for a specific BGP neighbor using two separate commands:
  - Received:   show bgp l2vpn evpn neighbor <ip> routes json   (JSON output)
  - Advertised: show bgp l2vpn evpn neighbor <ip> advertised-routes  (text output, parsed)

Requirements:
    pip install pytest paramiko

Run:
    pytest test_bgp_prefixes_sonic.py -v -s
"""

import json
import re
import pytest
import paramiko


# ===========================================================================
# CONFIGURATION — edit these variables before running
# ===========================================================================

DEVICE_IP      = "172.80.80.11"   # IP address of the SONiC device
SSH_USERNAME   = "admin"          # SSH username
SSH_PASSWORD   = "admin"          # SSH password
SSH_PORT       = 22               # SSH port (default: 22)
SSH_TIMEOUT    = 15               # Connection timeout in seconds

BGP_NEIGHBOR   = "10.0.2.1"      # BGP neighbor to inspect

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


def count_received_prefixes(raw: str) -> int:
    """
    Parses the JSON output of `show bgp l2vpn evpn neighbor <ip> routes json`
    and counts the total number of prefixes across all route distinguishers.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        pytest.fail(f"Could not parse EVPN routes JSON: {exc}\nRaw output:\n{raw}")

    # Use top-level numPrefix if available
    if "numPrefix" in data:
        return int(data["numPrefix"])

    # Otherwise count entries across all RDs in the routes dict
    routes = data.get("routes", {})
    total = 0
    for rd_entries in routes.values():
        if isinstance(rd_entries, list):
            total += len(rd_entries)
        elif isinstance(rd_entries, dict):
            total += len(rd_entries)
    return total


def count_advertised_prefixes(raw: str) -> int:
    """
    Parses the plain-text output of `show bgp l2vpn evpn neighbor <ip> advertised-routes`
    and counts prefix lines.

    A prefix line starts with a status code (* > i s d h) followed by a
    route in EVPN NLRI format, e.g.:
      *> [2]:[0]:[48]:[aa:c1:ab:7f:ba:bb]
      *> [3]:[0]:[32]:[10.0.1.1]
    """
    count = 0
    for line in raw.splitlines():
        # Match lines that begin with BGP status flags and an EVPN prefix [type]:...
        if re.match(r'^\s*[*>sidh]+\s+\[', line):
            count += 1
    return count


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def evpn_received_count():
    """Fetch received EVPN prefix count once over SSH for the entire test module."""
    raw = ssh_run_command(
        f"vtysh -c 'show bgp l2vpn evpn neighbor {BGP_NEIGHBOR} routes json'"
    )
    return count_received_prefixes(raw)


@pytest.fixture(scope="module")
def evpn_advertised_count():
    """Fetch advertised EVPN prefix count once over SSH for the entire test module."""
    raw = ssh_run_command(
        f"vtysh -c 'show bgp l2vpn evpn neighbor {BGP_NEIGHBOR} advertised-routes'"
    )
    return count_advertised_prefixes(raw)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def test_bgp_prefixes_received(evpn_received_count):
    """
    Report and verify that the number of EVPN prefixes received from
    the neighbor is retrievable (greater than or equal to 0).
    """
    print(f"\n BGP neighbour = {BGP_NEIGHBOR} , Prefixes Received = {evpn_received_count}")
    assert evpn_received_count >= 0, (
        f"Unexpected prefix received count for neighbor {BGP_NEIGHBOR}: {evpn_received_count}"
    )


def test_bgp_prefixes_advertised(evpn_advertised_count):
    """
    Report and verify that the number of EVPN prefixes advertised to
    the neighbor is retrievable (greater than or equal to 0).
    """
    print(f"\n BGP neighbour = {BGP_NEIGHBOR} , Prefixes Advertised = {evpn_advertised_count}")
    assert evpn_advertised_count >= 0, (
        f"Unexpected prefix advertised count for neighbor {BGP_NEIGHBOR}: {evpn_advertised_count}"
    )
