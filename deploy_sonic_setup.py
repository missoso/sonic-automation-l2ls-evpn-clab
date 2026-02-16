#!/usr/bin/env python3
"""
SONiC Remote Configuration via SSH
Configures multiple settings on a remote SONiC device:
- BGP IPv4 unicast routing
- IP addresses on interfaces
- VLAN creation and membership
- VXLAN tunnel configuration

Configuration: Edit the variables below with your device details.
"""

import paramiko
import sys

# ============================================================================
# CONFIGURATION - Edit these values for your environment
# ============================================================================
SONIC_HOST = "172.80.80.11"       # SONiC device IP address
SSH_USERNAME = "admin"             # SSH username
SSH_PASSWORD = "admin"              # SSH password
SSH_PORT = 22                      # SSH port (usually 22)

# BGP Configuration
BGP_ASN = "101"                    # BGP Autonomous System Number
BGP_ROUTER_ID = "10.0.1.1"         # BGP Router ID

# IP Address Configuration
LOOPBACK0_IP = "10.0.1.1/32"       # Loopback0 IP address
ETHERNET0_IP = "192.168.11.0/31"   # Ethernet0 IP address

# VLAN Configuration
VLAN_ID = "100"                    # VLAN ID
VLAN_NAME = "Vlan100"              # VLAN name (usually Vlan + ID)
VLAN_MEMBER_PORT = "Ethernet4"     # Port to add to VLAN
VLAN_TAGGING_MODE = "untagged"     # Tagging mode: 'tagged' or 'untagged'

# VXLAN Configuration
VXLAN_TUNNEL_NAME = "vtep"         # VXLAN tunnel name
VXLAN_SOURCE_IP = "10.0.1.1"       # VXLAN source IP
VXLAN_VNI = "100"                  # VNI (Virtual Network Identifier)
# ============================================================================


def apply_sonic_configuration(host, username, password, port=22):
    """
    Connect to remote SONiC device via SSH and apply all configurations.
    
    Args:
        host (str): SONiC device IP address
        username (str): SSH username
        password (str): SSH password
        port (int): SSH port (default 22)
    
    Returns:
        bool: True if successful, False otherwise
    """
    
    print(f"Connecting to SONiC device at {host}...")
    
    # Create the remote command to execute all configurations
    remote_command = f"""python3 << 'EOF'
from swsscommon import swsscommon

def configure_sonic():
    try:
        # Connect to CONFIG_DB
        config_db = swsscommon.ConfigDBConnector()
        config_db.connect()
        
        print('Connected to CONFIG_DB')
        print('=' * 70)
        
        # 1. Configure BGP
        print('1. Configuring BGP...')
        config_db.mod_entry('DEVICE_METADATA', 'localhost', {{
            'bgp_asn': '{BGP_ASN}',
            'router_id': '{BGP_ROUTER_ID}'
        }})
        print('   ✓ BGP ASN: {BGP_ASN}')
        print('   ✓ BGP Router ID: {BGP_ROUTER_ID}')
        
        # Enable IPv4 unicast address family
        config_db.set_entry('BGP_GLOBALS', 'default', {{'local_asn': '{BGP_ASN}'}})
        print('   ✓ BGP IPv4 unicast routing enabled')
        
        # 2. Configure Loopback0 interface
        print('2. Configuring Loopback0...')
        # Create loopback interface if it doesn't exist
        config_db.set_entry('LOOPBACK_INTERFACE', 'Loopback0', {{}})
        # Add IP address to Loopback0
        config_db.set_entry('LOOPBACK_INTERFACE', 'Loopback0|{LOOPBACK0_IP}', {{}})
        print('   ✓ Loopback0 IP: {LOOPBACK0_IP}')
        
        # 3. Configure Ethernet0 interface
        print('3. Configuring Ethernet0...')
        # Make sure interface entry exists
        config_db.set_entry('INTERFACE', 'Ethernet0', {{}})
        # Add IP address to Ethernet0
        config_db.set_entry('INTERFACE', 'Ethernet0|{ETHERNET0_IP}', {{}})
        print('   ✓ Ethernet0 IP: {ETHERNET0_IP}')
        
        # 4. Create VLAN
        print('4. Creating VLAN...')
        config_db.set_entry('VLAN', '{VLAN_NAME}', {{'vlanid': '{VLAN_ID}'}})
        print('   ✓ Created {VLAN_NAME} (VLAN ID: {VLAN_ID})')
        
        # 5. Add interface to VLAN
        print('5. Adding {VLAN_MEMBER_PORT} to {VLAN_NAME}...')
        config_db.set_entry('VLAN_MEMBER', '{VLAN_NAME}|{VLAN_MEMBER_PORT}', {{
            'tagging_mode': '{VLAN_TAGGING_MODE}'
        }})
        print('   ✓ {VLAN_MEMBER_PORT} added to {VLAN_NAME} ({VLAN_TAGGING_MODE})')
        
        # 6. Create VXLAN tunnel
        print('6. Creating VXLAN tunnel...')
        # Create VXLAN tunnel interface
        config_db.set_entry('VXLAN_TUNNEL', '{VXLAN_TUNNEL_NAME}', {{
            'src_ip': '{VXLAN_SOURCE_IP}'
        }})
        print('   ✓ VXLAN tunnel "{VXLAN_TUNNEL_NAME}" created')
        print('   ✓ Source IP: {VXLAN_SOURCE_IP}')
        
        # 7. Map VLAN to VNI
        print('7. Mapping {VLAN_NAME} to VNI {VXLAN_VNI}...')
        config_db.set_entry('VXLAN_TUNNEL_MAP', '{VXLAN_TUNNEL_NAME}|map_{VXLAN_VNI}', {{
            'vlan': '{VLAN_NAME}',
            'vni': '{VXLAN_VNI}'
        }})
        print('   ✓ {VLAN_NAME} mapped to VNI {VXLAN_VNI}')
        
        config_db.close()
        
        print('=' * 70)
        print('SUCCESS: All configurations applied successfully!')
        return True
        
    except Exception as e:
        print('ERROR: ' + str(e))
        import traceback
        traceback.print_exc()
        return False

# Execute configuration
if configure_sonic():
    exit(0)
else:
    exit(1)
EOF
"""
    
    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect to the device
        ssh.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=10
        )
        
        print(f"✓ Connected to {host}")
        print()
        
        # Execute the command
        print("Applying configurations...")
        print()
        stdin, stdout, stderr = ssh.exec_command(remote_command)
        
        # Get the output in real-time
        for line in stdout:
            print(line.strip())
        
        # Check for errors
        error = stderr.read().decode().strip()
        exit_status = stdout.channel.recv_exit_status()
        
        if error and exit_status != 0:
            print("\nErrors encountered:")
            print(error)
            ssh.close()
            return False
        
        # Close SSH connection
        ssh.close()
        print()
        print(f"✓ Disconnected from {host}")
        
        return exit_status == 0
        
    except paramiko.AuthenticationException:
        print(f"✗ Authentication failed - check username/password")
        return False
    except paramiko.SSHException as e:
        print(f"✗ SSH error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def display_configuration_summary():
    """Display a summary of configurations to be applied."""
    print()
    print("=" * 70)
    print("SONiC Configuration Summary")
    print("=" * 70)
    print(f"Target Device: {SONIC_HOST}")
    print()
    print("Configurations to apply:")
    print(f"  1. BGP Configuration:")
    print(f"     - ASN: {BGP_ASN}")
    print(f"     - Router ID: {BGP_ROUTER_ID}")
    print(f"     - IPv4 Unicast: Enabled")
    print(f"  2. Loopback Interface:")
    print(f"     - Loopback0: {LOOPBACK0_IP}")
    print(f"  3. Ethernet Interface:")
    print(f"     - Ethernet0: {ETHERNET0_IP}")
    print(f"  4. VLAN:")
    print(f"     - {VLAN_NAME} (ID: {VLAN_ID})")
    print(f"     - Member: {VLAN_MEMBER_PORT} ({VLAN_TAGGING_MODE})")
    print(f"  5. VXLAN Tunnel:")
    print(f"     - Tunnel: {VXLAN_TUNNEL_NAME}")
    print(f"     - Source IP: {VXLAN_SOURCE_IP}")
    print(f"     - VLAN {VLAN_ID} <-> VNI {VXLAN_VNI}")
    print("=" * 70)
    print()


def main():
    """Main function."""
    
    # Display configuration summary
    display_configuration_summary()
    
    # Confirm before proceeding (optional - comment out for automation)
    try:
        response = input("Proceed with configuration? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Configuration cancelled.")
            return 0
        print()
    except:
        # If running non-interactively, proceed automatically
        pass
    
    # Execute the configuration
    success = apply_sonic_configuration(
        host=SONIC_HOST,
        username=SSH_USERNAME,
        password=SSH_PASSWORD,
        port=SSH_PORT
    )
    
    print()
    print("=" * 70)
    if success:
        print("✓ All configurations completed successfully")
        print("=" * 70)
        return 0
    else:
        print("✗ Configuration failed")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())