# TVI EVE-NG Lab Setup & Synchronization Guide

Hệ thống EVE-NG Community dùng để mô phỏng toàn bộ đồ án TVI (HCMC, Hà Nội, Đà Nẵng, ISP Cloud). Hướng dẫn này đảm bảo cả 4 thành viên cài đặt chuẩn xác, không bị lỗi lệch phiên bản, lỗi thiếu RAM hoặc lỗi ảo hóa lồng nhau.

---

## 1. Cấu hình máy ảo EVE-NG (VMware Workstation Pro)

- **VMware Workstation Pro** (tải bản cá nhân miễn phí từ Broadcom).
- **CPU:** Cấp 6 – 8 vCPUs.
  - **BẮT BUỘC:** Tích chọn `Virtualize Intel VT-x/EPT or AMD-V/RVI` trong phần CPU Settings của máy ảo EVE-NG.
  - *Lưu ý Windows 11:* Nếu gặp lỗi *"Virtualized Intel VT-x/EPT is not supported"*, hãy tắt **Core Isolation / Memory Integrity**, tắt **Hyper-V** và **WSL2**.
- **RAM:** Cấp 10.240 MB – 12.288 MB (10 – 12 GB).
- **Network Adapters:**
  - **Adapter 1:** Bridged hoặc NAT (dùng để truy cập Web UI EVE-NG từ trình duyệt: `http://<EVE_IP>`).
  - **Adapter 2:** Custom: Specific virtual network -> chọn **VMnet1 (Host-Only)**. Adapter này dùng để kết nối trực tiếp laptop vào mạng quản trị VLAN 99 qua Cloud1.

---

## 2. Chuẩn bị Image Cisco vIOS & vIOS-L2

Dùng WinSCP hoặc FileZilla SFTP vào EVE-NG (`root` / `eve`), truy cập `/opt/unetlab/addons/qemu/` và tạo đúng tên thư mục:

1. **Router Cisco vIOS (L3):**
   - Thư mục: `/opt/unetlab/addons/qemu/vios-152M3/`
   - File đĩa: đổi tên thành `virtioa.qcow2` (hoặc `hda.qcow2`)
2. **Switch Cisco vIOS-L2 (L2):**
   - Thư mục: `/opt/unetlab/addons/qemu/viosl2-1524/`
   - File đĩa: đổi tên thành `virtioa.qcow2`
3. **Phân quyền bắt buộc (Mandatory):**
   Mở terminal SSH vào EVE-NG gõ lệnh:
   ```bash
   /opt/unetlab/wrapper/unl_wrapper -a fixpermissions
   ```

---

## 3. Quy chuẩn tài nguyên Node trong Lab

Khi add node trên giao diện EVE-NG, đặt thông số RAM để tiết kiệm tài nguyên máy:
- **vIOS Router (HCMC-EDGE, HANOI-RTR, DANANG-RTR, ISP-CLOUD):** RAM **512 MB**, CPU **1**.
- **vIOS-L2 Switch (CORE, DIST1, DIST2, HANOI-SW, DANANG-SW):** RAM **768 MB**, CPU **1**.
- **VPCS:** RAM mặc định (~0 MB).

> **QUY TẮC VÀNG KHỞI ĐỘNG (STAGGERED BOOTING):**
> Tuyệt đối **KHÔNG** bấm "Start all nodes" cùng một lúc vì vIOS-L2 khởi động đồng loạt sẽ làm CPU nhảy 100% và crash QEMU.
> Hãy bật theo từng nhóm 3–4 node, cách nhau 30 giây:
> 1. Đợt 1: Bật ISP-CLOUD-RTR01 + 3 Router biên (HCMC, Hanoi, DaNang).
> 2. Đợt 2: Bật HCMC-CORE-SW01 + HCMC-DIST-SW01/02.
> 3. Đợt 3: Bật các switch chi nhánh và máy trạm VPCS.

---

## 4. Kết nối Laptop vào Lab (Mạng Quản trị VLAN 99)

Để laptop chạy script Python `Automation/auto_provision.py` hoặc SSH trực tiếp vào các switch/router:
1. Trên Windows: Chạy script `EVE_Lab/scripts/setup_vmware_vmnet.ps1` bằng quyền Administrator. (Script sẽ gán IP tĩnh `192.168.1.100/24` cho VMnet1 và trỏ route `192.168.0.0/22` qua `192.168.1.1`).
2. Trên canvas EVE-NG: Click chuột phải -> `Network` -> chọn type **Management(Cloud1)** (tương ứng với interface `pnet1`).
3. Kéo dây từ node `Management(Cloud1)` vào cổng **Gi1/1** của `HCMC-CORE-SW01` (thuộc VLAN 99).
4. Kiểm tra: từ PowerShell laptop gõ:
   ```powershell
   ssh admin@192.168.1.10
   ```
   Nếu đăng nhập thành công vào `HCMC-CORE-SW01` tức là đường truyền tự động hóa đã thông suốt!
