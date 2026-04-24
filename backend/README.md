# 后端（Django + DRF + JWT）

## 环境
- Python：使用 conda 环境 `bs001-psycare`（见 `environment.yml`）
- 数据库：MySQL（Docker）
- 缓存：Redis（Docker）

## 启动步骤
在 `02-系统实现代码/`：

```bash
cp .env.example .env
docker compose up -d
```

在 `02-系统实现代码/backend/`：

```bash
conda env create -f environment.yml
conda run -n bs001-psycare python manage.py migrate
conda run -n bs001-psycare python manage.py seed_demo
conda run -n bs001-psycare python manage.py runserver 0.0.0.0:52517
```

健康检查：
```bash
curl -s http://127.0.0.1:52517/api/health/
```

