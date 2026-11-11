# Cisco vIOS Images for EVE-NG (TVI Enterprise Network Lab)

Thư mục này chứa 2 image Cisco chuẩn để chạy đồ án TVI trên EVE-NG Community:

1. **Router Cisco (Layer 3):**
   * File: `vios-adventerprisek9-m.spa.159-3.m6.qcow2` (~57 MB)
   * Phiên bản: Cisco IOSv Software Release 15.9(3)M6 (Chạy BGP, OSPF, GRE over IPsec, QoS MQC).
2. **Switch Cisco (Layer 2):**
   * File: `viosl2-adventerprisek9-m.SSA.high_iron_20180619.tgz` (~44 MB)
   * Phiên bản: Cisco IOSvL2 Switch (Chạy VLAN, 802.1Q Trunk, EtherChannel LACP, Rapid-PVST+, SVI, HSRP v2).

---

## Hướng dẫn nạp nhanh vào EVE-NG cho các thành viên trong nhóm:

Khi bạn clone repo này về máy, thực hiện 2 bước sau để nạp vào EVE-NG:

### Bước 1: Copy vào EVE-NG bằng WinSCP
Mở WinSCP kết nối vào EVE-NG (`root` / `eve`), mở đường dẫn bên phải:
```text
/opt/unetlab/addons/qemu/
```

* **Với Router:**
  * Tạo thư mục: `/opt/unetlab/addons/qemu/vios-adventerprisek9-m.spa.159-3.m6/`
  * Copy file `vios-adventerprisek9-m.spa.159-3.m6.qcow2` vào và đổi tên thành: `virtioa.qcow2`.
* **Với Switch:**
  * Copy file `viosl2-adventerprisek9-m.SSA.high_iron_20180619.tgz` vào thẳng `/opt/unetlab/addons/qemu/`.

### Bước 2: Chạy lệnh giải nén & cấp quyền trên console EVE-NG
Mở màn hình đen của EVE-NG (hoặc SSH vào root), copy-paste các lệnh sau:
```bash
# Giải nén switch L2
tar -xzf /opt/unetlab/addons/qemu/viosl2-adventerprisek9-m.SSA.high_iron_20180619.tgz -C /opt/unetlab/addons/qemu/
rm -f /opt/unetlab/addons/qemu/viosl2-adventerprisek9-m.SSA.high_iron_20180619.tgz

# Tạo định danh KVM và cấp quyền
echo -n "kvm" > /opt/unetlab/platform
/opt/unetlab/wrappers/unl_wrapper -a fixpermissions
```

Sau khi chạy xong, mở giao diện Web EVE-NG sẽ thấy cả **Cisco vIOS Router** và **Cisco vIOS Switch** sáng xanh sẵn sàng tạo Lab!
