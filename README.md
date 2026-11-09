# TechViet Innovations (TVI) - Advanced Enterprise Network Project
## Môn học: Computer Networking & Network Administration (HCMUT)

Dự án thiết kế và triển khai mạng quy mô doanh nghiệp đa chi nhánh (HCMC HQ, Hanoi Campus, Da Nang Logistics Hub, ISP Cloud) dựa trên nền tảng **EVE-NG Community**, thiết bị ảo hóa **Cisco vIOS (L3) & vIOS-L2**, tự động hóa bằng **Python (Netmiko & PyYAML)**.

---

## 1. Cấu trúc cây thư mục Repository (Chuẩn Nộp Bài)

```text
large_enterprise_network/
├── .gitignore                         <- Bỏ qua file rác, venv, temporary backups, logs
├── requirements.txt                   <- Thư viện Python chuẩn (netmiko, pyyaml, paramiko)
├── setup_env.ps1                      <- Script cài môi trường 1-click cho Windows
├── setup_env.sh                       <- Script cài môi trường 1-click cho Linux/macOS
├── README.md                          <- Tài liệu hướng dẫn này
├── docs/
│   ├── TVI_Task_Split_v2.html         <- Bản phân chia công việc & rubric chi tiết
│   └── TVI_Phan_Chia_Cong_Viec_v2.pdf <- Bản PDF phân chia công việc chuẩn
├── Design/
│   ├── TVI_IP_Addressing_Schema.md    <- Bảng phân bổ VLSM IPv4 & IPv6 GUA
│   ├── topology_notes.md              <- Bảng đấu nối port-to-port chi tiết
│   ├── TVI_Logical_Topology.drawio    <- File thiết kế Draw.io (P1)
│   ├── TVI_Logical_Topology.png       <- File xuất ảnh sơ đồ logic
│   └── TVI_Physical_Topology.png      <- File sơ đồ đấu nối vật lý
├── Configurations/
│   ├── README.md                      <- Quy tắc chỉnh sửa config và phân vùng Git
│   ├── HQ_Startup_Configs/            <- HCMC Core, Dist1, Dist2, Edge, ISP Cloud
│   ├── Hanoi_Startup_Configs/         <- Hanoi Router, Dist SW01, Access SW02
│   └── DaNang_Startup_Configs/        <- Da Nang Router, Campus SW01
├── Automation/
│   ├── inventory.yaml                 <- Khai báo danh sách thiết bị và IP quản trị
│   ├── auto_provision.py              <- Script tự động hóa Netmiko (Step 9)
│   ├── requirements.txt               <- Thư viện cho module automation
│   ├── backups/                       <- Nơi lưu trữ file config được backup tự động
│   └── logs/                          <- Log thực thi automation.log
├── Report/
│   └── TVI_Technical_Explanation_Report.pdf <- Báo cáo kỹ thuật tổng hợp
└── EVE_Lab/
    ├── README.md                      <- Hướng dẫn import lab, đặt tên image, RAM node
    ├── TVI_Lab.unl                    <- File topology lab xuất từ EVE-NG (P1)
    └── scripts/
        ├── setup_vmware_vmnet.ps1     <- Cấu hình VMnet1 để laptop SSH vào EVE
        └── eve_fix_permissions.sh     <- Fix permissions trong EVE-NG
```

---

## 2. Hướng dẫn Khởi tạo Môi trường (Quickstart)

### Bước 1: Thiết lập môi trường Python trên máy cá nhân
Mở PowerShell tại thư mục gốc repository và chạy:
```powershell
.\setup_env.ps1
```
Script sẽ tự động:
- Tạo môi trường ảo `.venv`
- Cài đặt đầy đủ `netmiko`, `pyyaml`, `paramiko`
- Kiểm tra tính tương thích và xác nhận không có lỗi

### Bước 2: Thiết lập kết nối Laptop vào EVE-NG (Mạng Quản trị)
Để chạy script Python từ laptop hoặc SSH trực tiếp vào thiết bị lab:
1. Mở PowerShell với quyền **Administrator**:
   ```powershell
   .\EVE_Lab\scripts\setup_vmware_vmnet.ps1
   ```
2. Đảm bảo máy ảo EVE-NG trên VMware có **Network Adapter 2** gán vào **VMnet1 (Host-Only)**.
3. Kéo dây từ `Management(Cloud1)` trên canvas EVE-NG vào cổng `Gi1/1` của `HCMC-CORE-SW01`.

### Bước 3: Khởi động Lab và Nạp Cấu hình (Source of Truth)
1. Bật EVE-NG Web UI (`http://<EVE_IP>`).
2. Mở file cấu hình tương ứng trong thư mục `Configurations/`.
3. Dán cấu hình vào `Startup-config` của từng node (hoặc paste trực tiếp vào terminal console).
4. Thiết bị đã có sẵn toàn bộ cấu hình chuẩn chỉ sau 2 phút!

---

## 3. Phân chia Công việc theo Rubric 10 Điểm (Sprint 7 Ngày)

| Thành viên | Phụ trách kỹ thuật | Nhiệm vụ chính | Sản phẩm bàn giao |
|:---:|:---|:---|:---|
| **Thành viên 1** | **Campus LAN & Services** (Bước 1, 3, 4) | Dựng file lab `.unl`, vẽ sơ đồ Draw.io, VLANs, LACP, Rapid-PVST+ (Core root), HSRP Gateway, DHCP Server & Relay. | `TVI_Lab.unl`, Sơ đồ `.drawio/.png`, file `.cfg` switch + DHCP. |
| **Thành viên 2** | **Routing & ISP Peering** (Bước 2, 5, 6-BGP) | Lập bảng VLSM chi tiết, OSPFv2 đa vùng, OSPF summarization, ISP BGP AS 65100, eBGP, IPv6 SLAAC & OSPFv3. | `TVI_IP_Addressing_Schema.md`, file `.cfg` routing router/switch. |
| **Thành viên 3** | **WAN Overlay & QoS** (Bước 6-Tunnel, 8) | GRE over IPsec (Tunnel 10 & 20), routing xuyên VPN, phân loại QoS MQC (DSCP EF VoIP, AF31 Video), LLQ WAN. | File `.cfg` Crypto & MQC, log kiểm thử QoS packet match counter. |
| **Thành viên 4** | **Security & Automation** (Bước 7, 9, 10) | NAT/PAT Overload, ACL cô lập Guest, L2 Security (Port Sec, Snooping, DAI), script Python `auto_provision.py`, tổng hợp báo cáo. | Module `Automation/`, file `.cfg` bảo mật, báo cáo PDF hoàn chỉnh. |

---

## 4. Kịch bản Chạy Thử Tự Động Hóa (Step 9 Demo)

Kích hoạt môi trường ảo:
```powershell
.\.venv\Scripts\Activate.ps1
```

Chạy script kiểm tra và cấu hình tự động:
```powershell
python Automation\auto_provision.py
```
*Tài khoản mặc định: `admin` / `Cisco123!`.*
Script sẽ:
1. Kết nối an toàn qua SSH tới tất cả 6 switch.
2. Tự động backup `show running-config` và `show ip interface brief` kèm timestamp vào `Automation/backups/`.
3. Tự động kiểm tra VLAN hiện có (Idempotent: chỉ thêm VLAN còn thiếu).
4. Đẩy cấu hình mẫu (NTP, Banner MOTD, Logging buffer).
5. Lưu cấu hình vào NVRAM (`write memory`).
6. Báo cáo tổng kết và ghi log đầy đủ tại `Automation/logs/automation.log`.
