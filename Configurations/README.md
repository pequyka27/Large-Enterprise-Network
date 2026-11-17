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

## 3. Áp dụng cấu hình bảo mật P4

Các file `.cfg` biểu diễn trạng thái startup hoàn chỉnh. Khi cập nhật thiết bị đang có standard ACL `NAT_INSIDE`, chuyển ACL sang extended trong cửa sổ triển khai phù hợp và kiểm tra các phiên NAT đang hoạt động trước khi thay đổi. Các khối P4 hiện dùng extended ACL để loại trừ mạng nội bộ và chỉ PAT nguồn của site tương ứng.

Trên HANOI-RND-SW02 và DANANG-LOG-SW01, triển khai DHCP Snooping cùng trust uplink trước, cho VPCS xin DHCP và kiểm tra `show ip dhcp snooping binding`, sau đó bật `ip arp inspection vlan 10,20,30,40`. Sau khi switch khởi động lại, cho các máy trạm gia hạn DHCP để tạo lại binding. Máy dùng IP tĩnh cần binding/ARP ACL phù hợp trước khi bật DAI trên cổng đó.

ACL `GUEST_IN` cho phép DHCP và DNS UDP/TCP tới `10.10.254.1`, chặn mạng nội bộ và quản trị rồi cho phép Internet. ACL `GUEST_V6_IN` bảo vệ mạng nội bộ IPv6, đồng thời cho phép Neighbor Discovery và DHCPv6. Kiểm tra bằng lưu lượng từ máy trạm Guest qua đúng gateway khi triển khai trên EVE.
