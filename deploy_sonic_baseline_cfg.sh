#!/bin/bash
scp configs/leaf1-config_baseline.json admin@172.80.80.11:/home/admin/
ssh admin@172.80.80.11 << EOF 
sudo mv leaf1-config.json /etc/sonic/config_db.json
sudo config reload -y
EOF