# 安全与权限测试记录（模板）

## 1) 权限隔离
| 角色 | 访问接口 | 预期 | 结果 | 备注 |
| --- | --- | --- | --- | --- |
| 学生 | /api/admin/users/ | 403 | 403 | quickcheck |
| 学生 | /api/backups/export/ | 403 | 403 | quickcheck |
| 辅导员 | /api/admin/users/ | 403 | 403 | quickcheck |
| 学院管理员 | /api/admin/users/ | 403 | 403 | quickcheck |
| 系统管理员 | /api/admin/users/ | 200 | 200 | quickcheck |

## 2) 敏感数据与备份访问控制
- 备份下载需权限校验：通过/不通过
- 未授权用户访问备份：通过/不通过

## 3) 审计日志
- 关键操作是否留痕：通过/不通过

## 4) 快速脚本
参考：`docs/scripts/security-quickcheck.sh`
