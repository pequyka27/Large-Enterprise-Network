# TVI IP Addressing & Subnetting Schema (IPv4 / IPv6)

Tài liệu này quy chuẩn hóa toàn bộ sơ đồ đánh địa chỉ mạng IP theo kỹ thuật **VLSM (Variable Length Subnet Masking)** và **IPv6 Global Unicast (GUA)** cho tập đoàn TechViet Innovations (TVI).

---

## 1. Bảng phân bổ IPv4 Tổng thể các Site

| Vị trí / Khu vực | Dải Subnet Gốc | Mục đích / Đối tượng sử dụng | Cơ chế Gateway |
|---|---|---|---|
| **Ho Chi Minh HQ** | `10.10.0.0/16` | Campus LAN HQ, Data Center, Ban Giám đốc | HSRP Virtual Gateway (.1) |
| **Hanoi Campus** | `10.20.0.0/16` | R&D Campus, AI Labs, Kỹ sư phần mềm | Subinterface Router (.1) |
| **Da Nang Hub** | `10.30.0.0/16` | Logistics Hub, Thiết bị kho, IoT Endpoints | Subinterface Router (.1) |
| **HCMC Management** | `192.168.1.0/24` | VLAN 99 - Quản trị Switch, Automation SSH | HSRP VIP 192.168.1.1 |
| **Hanoi Management** | `192.168.2.0/24` | VLAN 99 - Quản trị Switch Hà Nội | Subinterface 192.168.2.1 |
| **Da Nang Management** | `192.168.3.0/24` | VLAN 99 - Quản trị Switch Đà Nẵng | Subinterface 192.168.3.1 |
| **WAN Underlay P2P** | `203.0.113.0/30`<br>`198.51.100.0/30`<br>`192.0.2.0/30` | Đấu nối Public eBGP giữa Edge Routers và ISP | Point-to-Point (.1 ISP, .2 Edge) |
| **VPN Overlay Tunnels** | `10.255.255.0/30`<br>`10.255.255.4/30` | GRE/IPsec Tunnels: HQ ↔ HN, HQ ↔ ĐN | Virtual P2P |

---

## 2. Chi tiết VLSM Subnetting theo quy mô người dùng

### 2.1. Headquarters (HCMC) – Khối `10.10.0.0/16` (Quy mô: 2.000+ Users)
*Khả năng cấp phát thực tế tối đa: 65.534 IPs; Hiện tại quy hoạch 2.500+ host, còn dư chỗ mở rộng lớn.*

| VLAN | Tên VLAN | Subnet CIDR | Subnet Mask | Dải IP khả dụng (Usable Range) | Broadcast | Gateway (HSRP VIP) | IP DIST-SW01 (Active) | IP DIST-SW02 (Standby) |
|:---:|:---|:---|:---|:---|:---|:---:|:---:|:---:|
| **20** | `RND_ENGINEERING` | `10.10.0.0/22` | 255.255.252.0 | 10.10.0.1 – 10.10.3.254 (1022 hosts) | 10.10.3.255 | `10.10.0.1` | 10.10.0.2 | 10.10.0.3 |
| **10** | `EXEC_FINANCE` | `10.10.4.0/23` | 255.255.254.0 | 10.10.4.1 – 10.10.5.254 (510 hosts) | 10.10.5.255 | `10.10.4.1` | 10.10.4.2 | 10.10.4.3 |
| **40** | `GUEST` | `10.10.6.0/23` | 255.255.254.0 | 10.10.6.1 – 10.10.7.254 (510 hosts) | 10.10.7.255 | `10.10.6.1` | 10.10.6.2 | 10.10.6.3 |
| **30** | `LOGISTICS_OPS` | `10.10.8.0/24` | 255.255.255.0 | 10.10.8.1 – 10.10.8.254 (254 hosts) | 10.10.8.255 | `10.10.8.1` | 10.10.8.2 | 10.10.8.3 |
| **100** | `HQ_TRANSIT` | `10.10.255.0/29`| 255.255.255.248| 10.10.255.1 – 10.10.255.6 (6 hosts) | 10.10.255.7 | – | EDGE: .1 | DIST1: .2, DIST2: .3 |
| **Lo0**| *Loopbacks* | `10.10.254.0/24`| 255.255.255.0 | 10.10.254.1 – 10.10.254.254 | 10.10.254.255 | – | EDGE: .1 | DIST1: .2, DIST2: .3 |

---

### 2.2. Chi nhánh Hà Nội (Hanoi) – Khối `10.20.0.0/16` (Quy mô: 1.500+ Users)

| VLAN | Tên VLAN | Subnet CIDR | Subnet Mask | Dải IP khả dụng (Usable Range) | Broadcast | Gateway (Router Subinterface) |
|:---:|:---|:---|:---|:---|:---|:---:|
| **20** | `RND_ENGINEERING` | `10.20.0.0/22` | 255.255.252.0 | 10.20.0.1 – 10.20.3.254 (1022 hosts) | 10.20.3.255 | `10.20.0.1` (Gi0/1.20) |
| **40** | `GUEST` | `10.20.4.0/23` | 255.255.254.0 | 10.20.4.1 – 10.20.5.254 (510 hosts) | 10.20.5.255 | `10.20.4.1` (Gi0/1.40) |
| **10** | `EXEC_FINANCE` | `10.20.6.0/24` | 255.255.255.0 | 10.20.6.1 – 10.20.6.254 (254 hosts) | 10.20.6.255 | `10.20.6.1` (Gi0/1.10) |
| **30** | `LOGISTICS_OPS` | `10.20.7.0/26` | 255.255.255.192| 10.20.7.1 – 10.20.7.62 (62 hosts) | 10.20.7.63 | `10.20.7.1` (Gi0/1.30) |
| **Lo0**| *Loopback0* | `10.20.254.1/32`| 255.255.255.255| Router ID / Management | – | – |

---

### 2.3. Chi nhánh Đà Nẵng (Da Nang) – Khối `10.30.0.0/16` (500+ Users & 10.000+ IoT Scaling)

| VLAN | Tên VLAN | Subnet CIDR | Subnet Mask | Dải IP khả dụng (Usable Range) | Broadcast | Gateway (Router Subinterface) |
|:---:|:---|:---|:---|:---|:---|:---:|
| **30** | `LOGISTICS_OPS (+IoT)` | `10.30.0.0/22` | 255.255.252.0 | 10.30.0.1 – 10.30.3.254 (1022 hosts) | 10.30.3.255 | `10.30.0.1` (Gi0/1.30) |
| **40** | `GUEST` | `10.30.4.0/24` | 255.255.255.0 | 10.30.4.1 – 10.30.4.254 (254 hosts) | 10.30.4.255 | `10.30.4.1` (Gi0/1.40) |
| **10** | `EXEC_FINANCE` | `10.30.5.0/26` | 255.255.255.192| 10.30.5.1 – 10.30.5.62 (62 hosts) | 10.30.5.63 | `10.30.5.1` (Gi0/1.10) |
| **20** | `RND_ENGINEERING` | `10.30.5.64/27`| 255.255.255.224| 10.30.5.65 – 10.30.5.94 (30 hosts) | 10.30.5.95 | `10.30.5.65` (Gi0/1.20) |
| **IoT**| *Dự trữ mở rộng IoT* | `10.30.64.0/18`| 255.255.192.0 | 10.30.64.1 – 10.30.127.254 (16.382 hosts)| 10.30.127.255| *Reserved for Future IoT Hubs* |
| **Lo0**| *Loopback0* | `10.30.254.1/32`| 255.255.255.255| Router ID / Management | – | – |

---

## 3. Phân bổ IPv6 Global Unicast (GUA)
Khối IPv6 gốc doanh nghiệp: `2001:db8:7a1::/48`
Quy ước đánh địa chỉ chuẩn: `2001:db8:7a1:SVV::/64`
Trong đó:
- `S` = Mã Site (1: HCMC HQ, 2: Hanoi, 3: Da Nang)
- `VV` = VLAN ID (10, 20, 30, 40, 99; transit = ff)

| Vị trí / VLAN | Subnet IPv6 Prefix | Default Gateway IP | Ghi chú |
|---|---|---|---|
| HQ VLAN 10 (Finance) | `2001:db8:7a1:110::/64` | `2001:db8:7a1:110::1` | SLAAC / HSRPv2 |
| HQ VLAN 20 (R&D) | `2001:db8:7a1:120::/64` | `2001:db8:7a1:120::1` | SLAAC / HSRPv2 |
| HQ VLAN 30 (Logistics)| `2001:db8:7a1:130::/64` | `2001:db8:7a1:130::1` | SLAAC / HSRPv2 |
| HQ VLAN 40 (Guest) | `2001:db8:7a1:140::/64` | `2001:db8:7a1:140::1` | SLAAC / HSRPv2 |
| HQ Transit (VLAN 100)| `2001:db8:7a1:1ff::/64` | EDGE: `::1`, DIST1: `::2`, DIST2: `::3` | OSPFv3 Area 0 |
| Hanoi VLAN 20 (R&D) | `2001:db8:7a1:220::/64` | `2001:db8:7a1:220::1` | SLAAC (Gi0/1.20) |
| Da Nang VLAN 30 (Ops) | `2001:db8:7a1:330::/64` | `2001:db8:7a1:330::1` | SLAAC (Gi0/1.30) |
