# 数据备份与定时任务

本项目提供两种方式导出备份：

## 1) API 触发导出
- 学院管理员：`POST /api/backups/export/`（导出本学院）
- 系统管理员：`POST /api/backups/export/`（不传 `college_id` 导出全量）

## 2) 管理命令导出
在 `02-系统实现代码/backend/` 下执行：

```bash
conda run -n bs001-psycare python manage.py backup_export --college-id 1
conda run -n bs001-psycare python manage.py backup_export --all
```

备份文件默认输出到：`02-系统实现代码/storage/backups/`

## 3) 定时任务示例（cron）
以下示例每天凌晨 2 点执行全量备份：

```bash
0 2 * * * cd /path/to/02-系统实现代码/backend && conda run -n bs001-psycare python manage.py backup_export --all
```
