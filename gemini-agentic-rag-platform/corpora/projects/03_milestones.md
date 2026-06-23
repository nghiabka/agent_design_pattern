---
id: PROJ-003
title: Milestones và Blockers
corpus: projects
---

# Milestones và Blockers

## Project Phoenix — Milestones sắp tới

| Milestone | Deadline | Status | Owner |
|-----------|----------|--------|-------|
| MVP microservices architecture | 15/07/2025 | 🟡 At Risk | Vũ Minh Giang |
| Staging deployment on K8s | 01/08/2025 | 🔵 Not Started | Hoàng Thị Em (DevOps) |
| Performance testing | 15/08/2025 | 🔵 Not Started | Bùi Phương Linh |
| Production migration wave 1 | 01/09/2025 | 🔵 Not Started | Nguyễn Văn An |
| Go-live | 30/09/2025 | 🔵 Not Started | Trần Thị Bình |

### Blockers
1. **SRV-042 instability**: Staging environment trên SRV-042 bị ảnh hưởng bởi incidents liên tục. Cần migrate staging lên AWS EKS trước 01/08.
2. **DevOps bandwidth**: Team DevOps đang setup K8s cluster cho Phoenix nhưng cũng phải hỗ trợ DataHub go-live (30/06).
3. **Testing resource**: Bùi Phương Linh phải chia thời gian 50/50 giữa Phoenix và Atlas.

## Project Atlas — Milestones sắp tới

| Milestone | Deadline | Status | Owner |
|-----------|----------|--------|-------|
| Design review | 01/07/2025 | 🟢 On Track | Trần Thị Bình |
| API contracts finalized | 15/07/2025 | 🟢 On Track | Lý Ngọc Khánh |
| Alpha release | 30/09/2025 | 🔵 Not Started | Trần Thị Bình |
| Beta release | 30/11/2025 | 🔵 Not Started | Trần Thị Bình |

### Blockers
1. **Mobile developer vacancy**: Cần tuyển 1 React Native developer, đang phỏng vấn.
2. **API dependency**: Phụ thuộc vào Phoenix microservices API — nếu Phoenix delay thì Atlas cũng delay.

## Project DataHub — Milestones sắp tới

| Milestone | Deadline | Status | Owner |
|-----------|----------|--------|-------|
| UAT completion | 20/06/2025 | ✅ Done | Mai Thị Diệu |
| Go-live | 30/06/2025 | 🟢 On Track | Lê Hoàng Cường |
| Post-go-live support | 01-31/07/2025 | 🔵 Not Started | Team Data Engineering |

### Blockers
- Không có blocker nghiêm trọng. DataHub đang on-track cho go-live cuối tháng 6.
