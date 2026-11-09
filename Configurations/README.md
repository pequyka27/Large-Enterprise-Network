# TVI Configurations Directory Guide

Thư mục này chứa toàn bộ cấu hình chuẩn (`startup-config`) của từng thiết bị mạng trong đồ án TVI.

---

## 1. Nguyên tắc "Cấu hình là Nguồn Chuẩn" (Source of Truth)
- Vì nhóm **không thuê server chạy 24/7**, trạng thái máy ảo có thể bị tắt, xóa hoặc import lại bất kỳ lúc nào.
- Toàn bộ trạng thái của lab được lưu trữ dưới dạng **file văn bản thuần túy (.cfg)** trên Git.
- Khi muốn khôi phục thiết bị trên EVE-NG:
  1. Mở file `.cfg` tương ứng trong Git repo.
  2. Dán nội dung vào mục **Startup-config** của Node trong EVE-NG Web UI (hoặc paste trực tiếp vào cửa sổ Console).
  3. Node khởi động lên sẽ có đầy đủ IP, định tuyến và bảo mật chỉ sau 2 phút!

---

## 2. Quy tắc phân vùng Comment để tránh xung đột Git (Merge Conflicts)

Mỗi file cấu hình được phân tách rõ ràng thành 4 khối tương ứng với 4 thành viên:

```cisco
! ============================================================
! DEVICE: <HOSTNAME>
! ============================================================

! ------------------------------------------------------------
! [P1] CAMPUS LAN, VLANS, TRUNKING, STP & IP SERVICES
! Phụ trách: Thành viên 1
! ------------------------------------------------------------
...

! ------------------------------------------------------------
! [P2] ROUTING UNDERLAY, OSPF, BGP PEERING & IPV6
! Phụ trách: Thành viên 2
! ------------------------------------------------------------
...

! ------------------------------------------------------------
! [P3] WAN OVERLAY (GRE/IPSEC VPN) & QOS POLICIES
! Phụ trách: Thành viên 3
! ------------------------------------------------------------
...

! ------------------------------------------------------------
! [P4] SECURITY (NAT, ACLS, L2 SECURITY) & MANAGEMENT
! Phụ trách: Thành viên 4
! ------------------------------------------------------------
...
```

**LƯU Ý:**
- Thành viên phụ trách phần nào chỉ chỉnh sửa bên trong khối `[Px]` của mình.
- Không tự ý sửa đổi tên thiết bị, tên interface, hoặc địa chỉ IP cố định đã được thống nhất tại [TVI_IP_Addressing_Schema.md](../Design/TVI_IP_Addressing_Schema.md).
