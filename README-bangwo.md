# 盘搜帮我（pansou-bangwo）

基于 fish2018 的 PanSou / PanSou Web 搭建的独立新项目，用于网盘资源搜索。

## 项目命名

- 项目名：`pansou-bangwo`
- 中文名：盘搜帮我
- 后端目录：`backend/`
- 前端目录：`frontend/`

## 当前本机运行方式

### 后端

```bash
cd backend
PORT=8888 \
CACHE_PATH=$PWD/cache \
ENABLED_PLUGINS=labi,zhizhen,shandian,duoduo,muou \
CHANNELS=tgsearchers7 \
./pansou-bangwo
```

健康检查：

```bash
curl http://127.0.0.1:8888/api/health
```

### 前端开发服务

```bash
cd frontend
VITE_API_BASE_URL=http://127.0.0.1:8888 npm run dev -- --host 0.0.0.0 --port 3001
```

访问：

```text
http://127.0.0.1:3001/
```

## README 原始部署说明摘要

fish2018/pansou README 推荐 Docker：

- 前后端集成版：`docker run -d --name pansou -p 80:80 ghcr.io/fish2018/pansou-web`
- 纯后端 API：`docker run -d --name pansou -p 8888:8888 ghcr.io/fish2018/pansou:latest`

本机当前没有 Docker，所以先采用源码构建方式跑通。

## 验证结果

- 后端 `/api/health` 已返回 `status: ok`
- 前端 dev server 已可访问
- 前端 `/api/health` 代理到后端已验证通过
- 搜索 smoke test 已返回正常 JSON
