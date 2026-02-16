#!/bin/bash
ssh admin@172.80.80.11 << EOF 
vtysh
config terminal

no ip protocol bgp route-map RM_SET_SRC
no ip prefix-list PL_LoopbackV4
no route-map RM_SET_SRC

ip prefix-list all_routes seq 5 permit 0.0.0.0/0 le 32
ip prefix-list allow-lo0 seq 5 permit 10.0.1.1/32

route-map send-lo0 permit 10
 match ip address prefix-list allow-lo0
exit

route-map import-all permit 10
 match ip address prefix-list all_routes
exit

frr defaults traditional
hostname sonic
log syslog informational
log facility local4
no zebra nexthop kernel enable
fpm address 127.0.0.1
no fpm use-next-hop-groups
agentx
no service integrated-vtysh-config


password zebra
enable password zebra

ip router-id 10.0.1.1

router bgp 101
 bgp router-id 10.0.1.1
 bgp suppress-fib-pending
 bgp log-neighbor-changes
 bgp bestpath as-path multipath-relax
 bgp ebgp-requires-policy
 bgp default ipv4-unicast
 neighbor 10.0.2.1 remote-as 100
 neighbor 10.0.2.1 local-as 100
 neighbor 10.0.2.1 update-source 10.0.1.1
 neighbor 192.168.11.1 remote-as 201
 neighbor 192.168.11.1 update-source 192.168.11.0
 
 address-family ipv4 unicast
  network 10.0.1.1/32
  neighbor 10.0.2.1 activate
  neighbor 192.168.11.1 route-map import-all in
  neighbor 192.168.11.1 route-map send-lo0 out
 exit-address-family
 
 address-family l2vpn evpn
  neighbor 10.0.2.1 activate
  advertise-all-vni
  vni 100
   rd 10.0.1.1:100
   route-target import 65000:100
   route-target export 65000:100
  exit-vni
  advertise-svi-ip
 exit-address-family
exit

ip nht resolve-via-default

ipv6 nht resolve-via-default

exit
write memory

EOF