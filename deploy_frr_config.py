#!/usr/bin/env python3
"""
SONiC FRR Configuration via vtysh
Configures BGP, EVPN, route-maps, and prefix-lists using vtysh commands.
Supports both local and remote execution via SSH.
"""

import subprocess
import sys

# ============================================================================
# REMOTE CONNECTION CONFIGURATION
# ============================================================================
# Set REMOTE_EXECUTION to True to run on a remote SONiC device via SSH
# Set to False to run locally on the SONiC device

REMOTE_EXECUTION = True           # True = SSH to remote device, False = run locally
SONIC_HOST = "172.80.80.11"       # Remote SONiC device IP address
SSH_USERNAME = "admin"             # SSH username
SSH_PASSWORD = "admin"   # SSH password
SSH_PORT = 22                      # SSH port (usually 22)

# Alternative: Use SSH key instead of password
USE_SSH_KEY = False                # Set to True to use SSH key authentication
SSH_KEY_FILE = "~/.ssh/id_rsa"    # Path to SSH private key file
# ============================================================================

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
    if REMOTE_EXECUTION:
        print("Warning: paramiko not installed. Remote execution will not work.")
        print("Install with: pip install paramiko")


# ============================================================================
# REMOTE EXECUTION HELPER
# ============================================================================

def execute_remote_command(command, host, username, password=None, key_file=None, port=22):
    """
    Execute a command on a remote host via SSH.
    
    Args:
        command (str): Command to execute
        host (str): Remote host IP/hostname
        username (str): SSH username
        password (str): SSH password (optional if using key)
        key_file (str): Path to SSH private key (optional)
        port (int): SSH port
    
    Returns:
        tuple: (success, stdout, stderr)
    """
    if not PARAMIKO_AVAILABLE:
        print("✗ paramiko library not available for SSH")
        return False, "", "paramiko not installed"
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect with key or password
        if key_file:
            ssh.connect(
                hostname=host,
                port=port,
                username=username,
                key_filename=key_file,
                timeout=10
            )
        else:
            ssh.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=10
            )
        
        # Execute command
        stdin, stdout, stderr = ssh.exec_command(command, timeout=60)
        
        stdout_text = stdout.read().decode().strip()
        stderr_text = stderr.read().decode().strip()
        exit_status = stdout.channel.recv_exit_status()
        
        ssh.close()
        
        return exit_status == 0, stdout_text, stderr_text
        
    except Exception as e:
        return False, "", str(e)


# ============================================================================
# FRR CONFIGURATION VIA VTYSH
# ============================================================================

def configure_frr_vtysh():
    """
    Configure FRR using vtysh commands via subprocess.
    Supports both local and remote execution via SSH.
    """
    
    print("=" * 70)
    print("Configuring FRR using vtysh")
    if REMOTE_EXECUTION:
        print(f"Mode: Remote execution via SSH to {SONIC_HOST}")
    else:
        print("Mode: Local execution")
    print("=" * 70)
    print()
    
    # All FRR commands in order
    commands = [
        # Clean up existing configs
        "no ip protocol bgp route-map RM_SET_SRC",
        "no ip prefix-list PL_LoopbackV4",
        "no route-map RM_SET_SRC",
        
        # Prefix lists
        "ip prefix-list all_routes seq 5 permit 0.0.0.0/0 le 32",
        "ip prefix-list allow-lo0 seq 5 permit 10.0.1.1/32",
        
        # Route maps
        "route-map send-lo0 permit 10",
        "match ip address prefix-list allow-lo0",
        "exit",
        
        "route-map import-all permit 10",
        "match ip address prefix-list all_routes",
        "exit",
        
        # FRR defaults and global settings
        "frr defaults traditional",
        "hostname sonic",
        "log syslog informational",
        "log facility local4",
        "no zebra nexthop kernel enable",
        "fpm address 127.0.0.1",
        "no fpm use-next-hop-groups",
        "agentx",
        "no service integrated-vtysh-config",
        "password zebra",
        "enable password zebra",
        
        # Router ID
        "ip router-id 10.0.1.1",
        
        # BGP Configuration
        "router bgp 101",
        "bgp router-id 10.0.1.1",
        "bgp suppress-fib-pending",
        "bgp log-neighbor-changes",
        "bgp bestpath as-path multipath-relax",
        "bgp ebgp-requires-policy",
        "bgp default ipv4-unicast",
        
        # BGP Neighbors
        "neighbor 10.0.2.1 remote-as 100",
        "neighbor 10.0.2.1 local-as 100",
        "neighbor 10.0.2.1 update-source 10.0.1.1",
        "neighbor 192.168.11.1 remote-as 201",
        "neighbor 192.168.11.1 update-source 192.168.11.0",
        
        # IPv4 Unicast Address Family
        "address-family ipv4 unicast",
        "network 10.0.1.1/32",
        "neighbor 10.0.2.1 activate",
        "neighbor 192.168.11.1 route-map import-all in",
        "neighbor 192.168.11.1 route-map send-lo0 out",
        "exit-address-family",
        
        # L2VPN EVPN Address Family
        "address-family l2vpn evpn",
        "neighbor 10.0.2.1 activate",
        "advertise-all-vni",
        "vni 100",
        "rd 10.0.1.1:100",
        "route-target import 65000:100",
        "route-target export 65000:100",
        "exit-vni",
        "advertise-svi-ip",
        "exit-address-family",
        "exit",
        
        # Next-hop tracking
        "ip nht resolve-via-default",
        "ipv6 nht resolve-via-default",
    ]
    
    # Build vtysh command
    vtysh_cmd = ['sudo', 'vtysh', '-c', 'configure terminal']
    
    for cmd in commands:
        vtysh_cmd.extend(['-c', cmd])
    
    # Convert command list to single string for SSH execution
    vtysh_cmd_str = ' '.join([f"'{c}'" if ' ' in c else c for c in vtysh_cmd])
    
    print("Executing configuration commands...")
    
    try:
        if REMOTE_EXECUTION:
            # Execute remotely via SSH
            if not PARAMIKO_AVAILABLE:
                print("✗ Cannot execute remotely: paramiko not installed")
                print("   Install with: pip install paramiko")
                return False
            
            print(f"Connecting to {SONIC_HOST}...")
            success, stdout, stderr = execute_remote_command(
                vtysh_cmd_str,
                SONIC_HOST,
                SSH_USERNAME,
                SSH_PASSWORD if not USE_SSH_KEY else None,
                SSH_KEY_FILE if USE_SSH_KEY else None,
                SSH_PORT
            )
            
            if not success:
                print(f"✗ SSH connection or execution failed: {stderr}")
                return False
            
            print(f"✓ Connected to {SONIC_HOST}")
            
            if stdout:
                print("\nOutput:")
                print(stdout)
            if stderr:
                print("\nWarnings/Info:")
                print(stderr)
            
        else:
            # Execute locally
            result = subprocess.run(vtysh_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print("✗ Error executing configuration")
                if result.stderr:
                    print("Error output:")
                    print(result.stderr)
                return False
            
            if result.stdout:
                print("\nOutput:")
                print(result.stdout)
        
        print("✓ Configuration commands executed successfully")
        
        # Save configuration
        print("\nSaving configuration...")
        save_cmd = "sudo vtysh -c 'write memory'"
        
        if REMOTE_EXECUTION:
            success, stdout, stderr = execute_remote_command(
                save_cmd,
                SONIC_HOST,
                SSH_USERNAME,
                SSH_PASSWORD if not USE_SSH_KEY else None,
                SSH_KEY_FILE if USE_SSH_KEY else None,
                SSH_PORT
            )
            
            if success:
                print("✓ Configuration saved to memory")
                if stdout:
                    print(stdout)
                print()
                return True
            else:
                print(f"✗ Error saving configuration: {stderr}")
                return False
        else:
            save_result = subprocess.run(
                ['sudo', 'vtysh', '-c', 'write memory'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if save_result.returncode == 0:
                print("✓ Configuration saved to memory")
                print()
                return True
            else:
                print("✗ Error saving configuration")
                if save_result.stderr:
                    print(save_result.stderr)
                return False
            
    except subprocess.TimeoutExpired:
        print("✗ Command execution timed out")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


# ============================================================================
# Main execution
# ============================================================================

def main():
    """Main function to run FRR configuration."""
    
    print("\n" + "=" * 70)
    print("SONiC FRR Configuration Script")
    print("=" * 70)
    if REMOTE_EXECUTION:
        print(f"Target Device: {SONIC_HOST}")
        print(f"SSH Username : {SSH_USERNAME}")
        print(f"SSH Port     : {SSH_PORT}")
        if USE_SSH_KEY:
            print(f"Auth Method  : SSH Key ({SSH_KEY_FILE})")
        else:
            print(f"Auth Method  : Password")
    else:
        print("Execution Mode: Local")
    print("=" * 70)
    print()
    
    # Execute the configuration
    success = configure_frr_vtysh()
    
    print("=" * 70)
    if success:
        print("✓ FRR configuration completed successfully!")
        print("=" * 70)
        return 0
    else:
        print("✗ FRR configuration failed")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
