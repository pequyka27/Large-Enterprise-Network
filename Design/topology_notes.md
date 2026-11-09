# TVI Topology Wireup & Cabling Reference (for Draw.io & EVE-NG)

Tài liệu tham chiếu đấu nối cáp mạng (Port-to-Port Interconnect) giữa các thiết bị. Thành viên 1 tuân thủ tuyệt đối bảng này khi vẽ sơ đồ Draw.io và cắm dây trong lab EVE-NG.

---

## 1. Bảng đấu nối chi tiết (Cabling Matrix)

| Thiết bị nguồn (Device A) | Cổng A (Port A) | Thiết bị đích (Device B) | Cổng B (Port B) | Loại liên kết & Ghi chú |
|:---|:---|:---|:---|:---|
| **HCMC-EDGE-RTR01** | `Gi0/0` | **ISP-CLOUD-RTR01** | `Gi0/0` | WAN Underlay: `203.0.113.0/30` (eBGP) |
| **HCMC-EDGE-RTR01** | `Gi0/1` | **HCMC-CORE-SW01** | `Gi0/0` | LAN Transit: VLAN 100 (`10.10.255.0/29`) |
| **HCMC-CORE-SW01** | `Gi0/1` | **HCMC-DIST-SW01** | `Gi0/1` | Port-Channel 1 (LACP Active, 802.1Q Trunk) |
| **HCMC-CORE-SW01** | `Gi0/2` | **HCMC-DIST-SW01** | `Gi0/2` | Port-Channel 1 (LACP Active, 802.1Q Trunk) |
| **HCMC-CORE-SW01** | `Gi0/3` | **HCMC-DIST-SW02** | `Gi0/1` | Port-Channel 2 (LACP Active, 802.1Q Trunk) |
| **HCMC-CORE-SW01** | `Gi1/0` | **HCMC-DIST-SW02** | `Gi0/2` | Port-Channel 2 (LACP Active, 802.1Q Trunk) |
| **HCMC-DIST-SW01** | `Gi0/3` | **HCMC-DIST-SW02** | `Gi0/3` | Cross-Link Trunk (Dự phòng L2, Rapid-PVST block) |
| **HCMC-CORE-SW01** | `Gi1/1` | **MGMT (Cloud1/pnet1)** | `eth0` | Access VLAN 99 (Kết nối Laptop Automation) |
| **HCMC-DIST-SW01** | `Gi1/0` | **PC-HQ-EXEC** | `eth0` | Access VLAN 10 (`10.10.4.0/23`) |
| **HCMC-DIST-SW01** | `Gi1/1` | **PC-HQ-GUEST** | `eth0` | Access VLAN 40 (`10.10.6.0/23`) |
| **HCMC-DIST-SW02** | `Gi1/0` | **PC-HQ-RND** | `eth0` | Access VLAN 20 (`10.10.0.0/22`) |
| **HCMC-DIST-SW02** | `Gi1/1` | **PC-HQ-LOG** | `eth0` | Access VLAN 30 (`10.10.8.0/24`) |
| **HANOI-RND-RTR01** | `Gi0/0` | **ISP-CLOUD-RTR01** | `Gi0/1` | WAN Underlay: `198.51.100.0/30` (eBGP) |
| **HANOI-RND-RTR01** | `Gi0/1` | **HANOI-RND-SW01** | `Gi0/0` | Router-on-a-Stick Trunk (Subinterfaces .10, .20, .30, .40, .99) |
| **HANOI-RND-SW01** | `Gi0/1` | **HANOI-RND-SW02** | `Gi0/1` | Port-Channel 1 (LACP Active, 802.1Q Trunk) |
| **HANOI-RND-SW01** | `Gi0/2` | **HANOI-RND-SW02** | `Gi0/2` | Port-Channel 1 (LACP Active, 802.1Q Trunk) |
| **HANOI-RND-SW01** | `Gi1/0` | **PC-HN-EXEC** | `eth0` | Access VLAN 10 (`10.20.6.0/24`) |
| **HANOI-RND-SW02** | `Gi1/0` | **PC-HN-RND** | `eth0` | Access VLAN 20 (`10.20.0.0/22`) |
| **HANOI-RND-SW02** | `Gi1/1` | **PC-HN-GUEST** | `eth0` | Access VLAN 40 (`10.20.4.0/23`) |
| **DANANG-LOG-RTR01** | `Gi0/0` | **ISP-CLOUD-RTR01** | `Gi0/2` | WAN Underlay: `192.0.2.0/30` (eBGP) |
| **DANANG-LOG-RTR01** | `Gi0/1` | **DANANG-LOG-SW01** | `Gi0/0` | Router-on-a-Stick Trunk (Subinterfaces .10, .20, .30, .40, .99) |
| **DANANG-LOG-SW01** | `Gi1/0` | **PC-DN-LOG** | `eth0` | Access VLAN 30 (`10.30.0.0/22`) |
| **DANANG-LOG-SW01** | `Gi1/1` | **PC-DN-GUEST** | `eth0` | Access VLAN 40 (`10.30.4.0/24`) |

---

## 2. Quy tắc cổng không sử dụng (Blackhole Port Hardening)
- Mọi cổng Ethernet không xuất hiện trong bảng trên:
  1. Gán vào `VLAN 999` (`BLACKHOLE`).
  2. Bật chế độ truy cập: `switchport mode access`.
  3. Tắt cổng: `shutdown`.
