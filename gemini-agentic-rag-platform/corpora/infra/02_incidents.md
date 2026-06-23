---
id: INFRA-002
title: Incident Log Tháng 5/2025
corpus: infra
---

# Incident Log Tháng 5/2025

## Tổng kết
- Tổng số incident: 23
- P1 (Critical): 2
- P2 (High): 5
- P3 (Medium): 9
- P4 (Low): 7

## Server có incident nhiều nhất: SRV-042 (12 incidents)

### Chi tiết SRV-042
| Ngày | Severity | Mô tả | Thời gian downtime | Người xử lý |
|------|----------|-------|---------------------|-------------|
| 03/05 | P2 | CPU spike 98%, app response > 5s | 25 phút | Trần Đức Bảo |
| 05/05 | P3 | Disk I/O latency cao | 0 phút | Trần Đức Bảo |
| 08/05 | P1 | OOM kill — app crash toàn bộ | 45 phút | Nguyễn Văn An, Trần Đức Bảo |
| 10/05 | P3 | SSL certificate sắp hết hạn (7 ngày) | 0 phút | Ngô Hải Long |
| 12/05 | P4 | Log rotation failed | 0 phút | Ngô Hải Long |
| 15/05 | P2 | Memory leak detected, restart required | 15 phút | Trần Đức Bảo |
| 18/05 | P3 | Connection pool exhausted | 10 phút | Trần Đức Bảo |
| 20/05 | P4 | Cron job backup chạy chậm | 0 phút | Ngô Hải Long |
| 22/05 | P3 | High error rate trên API endpoint /v2/orders | 5 phút | Trần Đức Bảo |
| 25/05 | P1 | Network interface flapping, mất kết nối 3 lần | 30 phút | Phạm Quốc Duy |
| 27/05 | P4 | Prometheus exporter crash | 0 phút | Ngô Hải Long |
| 30/05 | P3 | Docker container restart loop | 8 phút | Trần Đức Bảo |

### Các server khác
| Server | Số incident | Severity cao nhất |
|--------|------------|-------------------|
| SRV-041 | 4 | P3 |
| SRV-043 | 3 | P2 |
| SRV-044 | 2 | P4 |
| SRV-051 | 1 | P3 |
| SRV-052 | 1 | P4 |

## Root Cause Analysis
SRV-042 có số incident cao bất thường do:
1. Chạy quá nhiều microservice trên cùng một host (15 containers).
2. Memory 128 GB không đủ cho workload hiện tại, cần upgrade lên 256 GB.
3. Đề xuất: migrate 5 service sang SRV-051 (DR) hoặc mua thêm server mới.
