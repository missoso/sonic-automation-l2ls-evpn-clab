# SONiC Automation (l2ls-evpn clab)

> [!NOTE]
> The key goal of this repository is to explore how to automate a SONiC device that is running BGP and part of an EVPN L2 deployment. The focus is on the automation component and not really on the EVPN deployment, reason why such deployment is very simplistic. The EVPN component itself is an EVPN L2LS interoperability scenario between **SONiC** and **Nokia SR Linux**.

## 📋 Overview

This lab simulates a small Data Center fabric with:
- **Spine:** Nokia SR Linux
- **Leaf 1:** SONiC (Virtual Switch)
- **Leaf 2:** Nokia SR Linux
- **Clients:** Linux Alpine hosts

The goal is to establish L2 EVPN connectivity between Client 1 (connected to SONiC) and Client 2 (connected to SR Linux).

### Topology

![Topology](./img_and_drawio/sonic-l2ls-evpn-containerlab.png)

## 🛠️ Prerequisites & Image Setup

To deploy the lab you will required have [Containerlab](https://containerlab.dev/install/) and [Docker](https://docs.docker.com/engine/install/) installed.

Additionally you will require a SONiC image that can be run in ContainerLab, if you don't have one this [repository](https://github.com/missoso/sonic-l2ls-evpn-containerlab?tab=readme-ov-file#%EF%B8%8F-prerequisites--image-setup) details step by step how to build one.

The automation will be deployed using [Python3](https://www.python.org/downloads/) using the [Paramiko](https://www.paramiko.org/) package for the SSH connection. The python script will invoke methods that require a SONiC image with the [sonic-swss-common](https://github.com/sonic-net/sonic-swss-common) (Switch State Service Common Library) package which should be part of the image, if not follow the link for installation instructions.

## 🚀 Deployment & Quick Start

### 1. Deploy the Topology

The [`evpn_sonic_l2ls.clab.yml`](./evpn_sonic_l2ls.clab.yml) file declaratively describes the lab.

Before deploying check if the SONiC image planned to be used matches the one specified in the topology file

```bash
    leaf1:
      kind: sonic-vm
      image: vrnetlab/sonic_sonic-vs:202411
```

To deploy the lab:

```bash
sudo containerlab deploy --reconfigure
```

```bash
╭─────────┬────────────────────────────────────┬───────────┬────────────────╮
│   Name  │             Kind/Image             │   State   │ IPv4/6 Address │
├─────────┼────────────────────────────────────┼───────────┼────────────────┤
│ client1 │ linux                              │ running   │ 172.80.80.32   │
│         │ ghcr.io/srl-labs/network-multitool │           │ N/A            │
├─────────┼────────────────────────────────────┼───────────┼────────────────┤
│ client2 │ linux                              │ running   │ 172.80.80.33   │
│         │ ghcr.io/srl-labs/network-multitool │           │ N/A            │
├─────────┼────────────────────────────────────┼───────────┼────────────────┤
│ leaf1   │ sonic-vm                           │ running   │ 172.80.80.11   │
│         │ vrnetlab/sonic_sonic-vs:202411     │ (healthy) │ N/A            │
├─────────┼────────────────────────────────────┼───────────┼────────────────┤
│ leaf2   │ nokia_srlinux                      │ running   │ 172.80.80.12   │
│         │ ghcr.io/nokia/srlinux:24.10.1      │           │ N/A            │
├─────────┼────────────────────────────────────┼───────────┼────────────────┤
│ spine1  │ nokia_srlinux                      │ running   │ 172.80.80.21   │
│         │ ghcr.io/nokia/srlinux:24.10.1      │           │ N/A            │
╰─────────┴────────────────────────────────────┴───────────┴────────────────╯
```

> [!IMPORTANT]
> **Wait for SONiC to boot.** It takes time. Check health status:
> ```bash
> docker ps | grep leaf1
> # Look for "(healthy)" status
> ```

### 2. Configure SONiC (Post-Boot)

Unlike SR Linux, SONiC needs post-boot configuration.

**Step A: Apply a baseline System Configuration (JSON)**

This step deploys the actions specified in the script [`deploy_sonic_baseline_cfg.sh`](./deploy_sonic_baseline_cfg.sh).

*What this does:*
1. Copies [`configs/leaf1-config_baseline.json`](./configs/leaf1-config_baseline.json)to the host.
2. Replaces `/etc/sonic/config_db.json` in the SONiC switch
3. Reloads configuration (`sudo config reload -y`).

```bash
sh deploy_sonic_baseline_cfg.sh
```

The contents of the leaf1-config_baseline.json are to simulate a box without any BGP or interface layer 3 configuraiton, the reason why this step is required is that many SONiC images have startup configurations files that include some baseline BGP and/or interfaces configuration. Removing them ensures that the SONiC device protocols and interfaces need to be configured from scratch.

**Step B: Apply Baseline BGP, Interfaces and VXLAN configuration**

To perform this step we will use the script [`deploy_sonic_setup.py`](./deploy_sonic_setup.py)

```bash
python3 deploy_sonic_setup.py
```

The above script communicates with the SONiC host via SSH and uses the sonic-swss-common package to change the SONiC switch configuration. 

The advantage is besides being able to use try/catch python logic when building the provisioning workflow it also allows access to methods that interact directly with the switch configuration as opposed of just copy/pasting commands into the CLI (which is what we will need to do for the FRR component)

Example: 
```bash
        # Connect to CONFIG_DB
        config_db = swsscommon.ConfigDBConnector()
        config_db.connect()
        [...]]        
        # Create loopback interface if it doesn't exist
        config_db.set_entry('LOOPBACK_INTERFACE', 'Loopback0', {{}})
        # Add IP address to Loopback0
        config_db.set_entry('LOOPBACK_INTERFACE', 'Loopback0|{LOOPBACK0_IP}', {{}})
```

A second variant of the script is To perform this step we will use the script [`deploy_sonic_setup_with_config_save.py`](./deploy_sonic_setup_with_config_save.py), the sole difference is that it will perform a "sudo config save -y" which saves the CONFIG_DB to config_db.json, similar to a copy of the running configuration into the startup configuration


**Step C: Apply Routing Configuration (FRR)**

There is no Python package to automate the deployment of the FRR component, so here the method used is the script [`deploy_bgp_vtysh.sh`](./deploy_bgp_vtysh.sh) which performs SSH and then paste BGP/EVPN commands into the `vtysh` CLI

```bash
sh deploy_bgp_vtysh.sh
```

**Step D: Populate ARP tables (FRR)**

Run the script [`pings.sh`](./pings.sh) to perform pings between the hosts 

```bash
sh pings.sh
```

### 3. Summary of Deployment Steps
1.  Deploy containerlab.
2.  Run [`deploy_sonic_baseline_cfg.sh`](./deploy_sonic_baseline_cfg.sh) (Updates JSON to simulate "factory reset").
3.  Run [`deploy_sonic_setup.py`](./deploy_sonic_setup.py) to add interfaces, VXLAN and BGP baseline configuration liek router ID and AS number to SONiC
4.  Run [`deploy_bgp_vtysh.sh`](./deploy_bgp_vtysh.sh) to deploy the FRR component
5.  Run [`pings.sh`](./pings.sh) (Populates ARP and verifies).

## 🧠 Deep Dive: SONiC Configuration & Architecture

### Interface Mapping (Containerlab vs SONiC)

In `evpn_sonic_l2ls.clab.yml`, interfaces are named `eth1`, `eth2`...
In SONiC, they map to `Ethernet0`, `Ethernet4`...

| Containerlab | SONiC Interface | Connected To |
| :--- | :--- | :--- |
| `eth1` | `Ethernet0` | Spine1 |
| `eth2` | `Ethernet4` | Client1 |

**Verification on SONiC:**
```bash
admin@sonic:~$ show interfaces status 
  Interface            Lanes       Speed    MTU    FEC           Alias    Vlan    Oper    Admin    Type    Asym PFC
-----------  ---------------  ----------  -----  -----  --------------  ------  ------  -------  ------  ----------
  Ethernet0      25,26,27,28  4294967.3G   9100    N/A    fortyGigE0/0  routed      up       up     N/A         N/A
  Ethernet4      29,30,31,32  4294967.3G   9100    N/A    fortyGigE0/4   trunk      up       up     N/A         N/A
  Ethernet8      33,34,35,36         40G   9100    N/A    fortyGigE0/8  routed    down       up     N/A         N/A
```

### Configuration Structure: JSON vs FRR

SONiC configuration is split between two key files.

#### 1. JSON Configuration (`/etc/sonic/config_db.json`)
Handles system state, interfaces, and basic BGP globals.

**Key JSON Snippets:**

*Global BGP Settings:*
```json
    "BGP_DEVICE_GLOBAL": {
        "STATE": {
            "idf_isolation_state": "unisolated",
            "tsa_enabled": "false",
            "wcmp_enabled": "false"
        }
    },
    "BGP_GLOBALS": {
        "default": {
            "default_ipv4_unicast": "true",
            "local_asn": "101",
            "router_id": "10.0.1.1"
        }
    }
```

*Device Metadata:*
```json
    "DEVICE_METADATA": {
        "localhost": {
            "bgp_asn": "101",
            "hostname": "sonic",
            "hwsku": "Force10-S6000",
            "mac": "22:d1:c7:63:8f:4a",
            "platform": "x86_64-kvm_x86_64-r0",
            "type": "LeafRouter"
        }
    }
```

> [!NOTE]
> The [SONiC Configuration Wiki](https://github.com/sonic-net/SONiC/wiki/Configuration) provides insights, but there is no single complete schema definition.

#### 2. FRR Configuration (`vtysh`)
Handles complex routing logic (Route Maps, Neighbors, EVPN).

```bash
admin@sonic:~$ vtysh
Hello, this is FRRouting (version 10.0.1).
sonic#
```

Some BGP options (like import/export policies) **must** be configured here, as they are not fully supported in the JSON config.

### VXLAN Configuration Details

We map VLAN 100 to VNI 100.

**JSON Configuration:**
```json
    "VLAN": { "Vlan100": { "vlanid": "100" } },
    "VLAN_MEMBER": { "Vlan100|Ethernet4": { "tagging_mode": "untagged" } },
    "VXLAN_TUNNEL": { "VXLAN100": { "src_ip": "10.0.1.1" } },
    "VXLAN_TUNNEL_MAP": { "VXLAN100|map_100_Vlan100": { "vlan": "Vlan100", "vni": "100" } }
```

**Equivalent CLI Commands:**
```bash
sudo config vlan add 100
sudo config vlan member add 100 Ethernet4 --untagged
sudo config vxlan add VXLAN100 10.0.1.1
sudo config vxlan map add VXLAN100 100 100
```

**Verification:**
```bash
admin@sonic:~$ show vxlan interface
VTEP Information:
	VTEP Name : VXLAN100, SIP  : 10.0.1.1
	Source interface  : Loopback0

admin@sonic:~$ show vlan brief
+-----------+--------------+-----------+----------------+-------------+
|   VLAN ID | IP Address   | Ports     | Port Tagging   | Proxy ARP   |
+===========+==============+===========+================+=============+
|       100 |              | Ethernet4 | untagged       | disabled    |
+-----------+--------------+-----------+----------------+-------------+
```

## ✅ Verification & Routing Table

### 1. Connectivity
Run the ping script to verify Client 1 (SONiC) <-> Client 2 (SRL).

```bash
./pings.sh
```

### 2. BGP EVPN Table
Verify that routes are exchanged between PE1 (SONiC - 10.0.1.1) and PE2 (SR Linux - 10.0.1.2).

```bash
admin@sonic:~$ vtysh -c "show bgp l2vpn evpn"

BGP table version is 6, local router ID is 10.0.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal
   Network          Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 10.0.1.1:100
 *> [2]:[0]:[48]:[22:d1:c7:63:8f:4a]:[128]:[fe80::20d1:c7ff:fe63:8f4a]
                    10.0.1.1                           32768 i
                    ET:8 RT:65000:100
 *> [2]:[0]:[48]:[aa:c1:ab:d7:8a:06]
                    10.0.1.1                           32768 i
                    ET:8 RT:65000:100
Route Distinguisher: 10.0.1.2:100
 *> [2]:[0]:[48]:[aa:c1:ab:5a:c3:78]
                    10.0.1.2                      100      0 100 201 i
                    RT:65000:100 ET:8
```

## 🧹 Cleanup

To stop the lab and remove all containers:

```bash
sudo containerlab destroy -t evpn_sonic_l2ls.clab.yml --cleanup
```
