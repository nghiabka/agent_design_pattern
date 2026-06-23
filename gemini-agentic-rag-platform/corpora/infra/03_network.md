---
id: INFRA-003
title: Network Topology và Bảo mật
corpus: infra
---

# Network Topology và Bảo mật

## Kiến trúc mạng

```
Internet
  → Cloudflare WAF
  → Load Balancer (SRV-041 / SRV-051 DR)
  → Application Layer (SRV-042 / SRV-052 DR)
  → Database Layer (SRV-043 primary, SRV-044 replica)
```

## VPN Access
- Tất cả nhân viên remote phải kết nối qua WireGuard VPN.
- VPN endpoint: vpn.techvn.internal:51820
- IP range nội bộ: 10.0.0.0/16
- DC Hà Nội: 10.0.1.0/24
- DC TP.HCM: 10.0.2.0/24
- Nhân viên remote: 10.0.10.0/24

## Firewall Rules
- Chỉ cho phép port 443 (HTTPS) từ internet vào Load Balancer.
- Database server chỉ accept connection từ Application Layer (10.0.1.0/24).
- SSH access (port 22) chỉ từ VPN range (10.0.0.0/16).
- Monitoring (Prometheus port 9090, Grafana port 3000) chỉ truy cập qua VPN.

## Backup & DR
- RPO (Recovery Point Objective): 1 giờ.
- RTO (Recovery Time Objective): 4 giờ.
- Database replication: synchronous từ SRV-043 sang SRV-044.
- Cross-DC replication: asynchronous sang DC TP.HCM, lag tối đa 5 phút.
- DR drill: thực hiện mỗi quý, lần gần nhất 15/04/2025.
