---
id: INFRA-001
title: Danh sách Server và Cấu hình
corpus: infra
---

# Danh sách Server và Cấu hình

## Data Center Hà Nội

| Server ID | Hostname | CPU | RAM | Storage | OS | Vai trò |
|-----------|----------|-----|-----|---------|-----|---------|
| SRV-041 | hn-web-01 | 32 cores | 64 GB | 2 TB SSD | Ubuntu 22.04 | Web Server, Load Balancer |
| SRV-042 | hn-app-01 | 64 cores | 128 GB | 4 TB SSD | Ubuntu 22.04 | Application Server chính |
| SRV-043 | hn-db-01 | 64 cores | 256 GB | 8 TB NVMe | Rocky Linux 9 | PostgreSQL Primary |
| SRV-044 | hn-db-02 | 64 cores | 256 GB | 8 TB NVMe | Rocky Linux 9 | PostgreSQL Replica |

## Data Center TP.HCM

| Server ID | Hostname | CPU | RAM | Storage | OS | Vai trò |
|-----------|----------|-----|-----|---------|-----|---------|
| SRV-051 | hcm-web-01 | 32 cores | 64 GB | 2 TB SSD | Ubuntu 22.04 | Web Server DR |
| SRV-052 | hcm-app-01 | 64 cores | 128 GB | 4 TB SSD | Ubuntu 22.04 | Application Server DR |

## Thông tin chung
- Tất cả server production đều có monitoring qua Prometheus + Grafana.
- Backup chạy hàng ngày lúc 2:00 AM, retention 30 ngày.
- Uptime SLA target: 99.9% cho production.
- Chi phí colocation DC Hà Nội: 45 triệu VND/tháng, DC TP.HCM: 35 triệu VND/tháng.
