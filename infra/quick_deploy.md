# FL-CL Quick Deployment Commands Reference

This file provides ready-to-use copy-paste commands to fetch and execute all the infrastructure scripts directly from the GitHub repository.

---

## 1. Host Configuration (Run on Proxmox Nodes)

### Enable VLAN Awareness
```bash
curl -L -O https://raw.githubusercontent.com/rhaffle87/fl-cl/refs/heads/main/infra/01_host_config/enable_vlan.sh
chmod +x enable_vlan.sh
./enable_vlan.sh
```

### Enable Hookscript Snippets
```bash
curl -L -O https://raw.githubusercontent.com/rhaffle87/fl-cl/refs/heads/main/infra/01_host_config/enable_snippets.sh
chmod +x enable_snippets.sh
./enable_snippets.sh
```

---

## 2. VM Provisioning (Run on Proxmox Hosts)

### Create FL Aggregator Container (LXC 300)
```bash
curl -L -O https://raw.githubusercontent.com/rhaffle87/fl-cl/refs/heads/main/infra/02_vm_provision/create_aggregator.sh
chmod +x create_aggregator.sh
./create_aggregator.sh
```

### Create Defender Node A (VM 310)
```bash
curl -L -O https://raw.githubusercontent.com/rhaffle87/fl-cl/refs/heads/main/infra/02_vm_provision/create_defender_a.sh
chmod +x create_defender_a.sh
./create_defender_a.sh
```

### Create Defender Node B (VM 320)
```bash
curl -L -O https://raw.githubusercontent.com/rhaffle87/fl-cl/refs/heads/main/infra/02_vm_provision/create_defender_b.sh
chmod +x create_defender_b.sh
./create_defender_b.sh
```

### Create Target Host A1 (VM 311)
```bash
curl -L -O https://raw.githubusercontent.com/rhaffle87/fl-cl/refs/heads/main/infra/02_vm_provision/create_target_a1.sh
chmod +x create_target_a1.sh
./create_target_a1.sh
```

### Create Target Host B1 (VM 321)
```bash
curl -L -O https://raw.githubusercontent.com/rhaffle87/fl-cl/refs/heads/main/infra/02_vm_provision/create_target_b1.sh
chmod +x create_target_b1.sh
./create_target_b1.sh
```

### Create Traffic Generator (VM 400)
```bash
curl -L -O https://raw.githubusercontent.com/rhaffle87/fl-cl/refs/heads/main/infra/02_vm_provision/create_traffic_gen.sh
chmod +x create_traffic_gen.sh
./create_traffic_gen.sh
```

---

## 3. Hookscripts Setup (Run on Proxmox Hosts)

### Port Mirroring Hookscript for Org A
```bash
curl -L -O https://raw.githubusercontent.com/rhaffle87/fl-cl/refs/heads/main/infra/03_hookscripts/mirror-hook-a.sh
chmod +x mirror-hook-a.sh
./mirror-hook-a.sh
```

### Port Mirroring Hookscript for Org B
```bash
curl -L -O https://raw.githubusercontent.com/rhaffle87/fl-cl/refs/heads/main/infra/03_hookscripts/mirror-hook-b.sh
chmod +x mirror-hook-b.sh
./mirror-hook-b.sh
```

---

## 4. Guest Setup (Run inside VMs/Containers)

### Aggregator Guest Setup (LXC 300)
```bash
curl -L -O https://raw.githubusercontent.com/rhaffle87/fl-cl/refs/heads/main/infra/04_guest_setup/setup_aggregator.sh
chmod +x setup_aggregator.sh
./setup_aggregator.sh
```

### Defender Guest Setup (VM 310 & VM 320)
```bash
curl -L -O https://raw.githubusercontent.com/rhaffle87/fl-cl/refs/heads/main/infra/04_guest_setup/setup_defender.sh
chmod +x setup_defender.sh
./setup_defender.sh
```

### Traffic Generator Guest Setup (VM 400)
```bash
curl -L -O https://raw.githubusercontent.com/rhaffle87/fl-cl/refs/heads/main/infra/04_guest_setup/setup_traffic_gen.sh
chmod +x setup_traffic_gen.sh
./setup_traffic_gen.sh
```
