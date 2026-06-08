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

## 线上长期部署方案

当前线上形态：

- 代码托管：GitHub `risk443/pansou-bangwo`
- 前端：Cloudflare Pages 项目 `pansou-bangwo`
- 正式访问：`https://pansou-bangwo.pages.dev/`
- API 路由：前端 Pages Functions 代理同源 `/api/*` 到后端公网地址
- 后端：Go API 服务，监听 `8888`，需要稳定公网入口

Cloudflare Pages 必须配置后端地址：

```bash
cd frontend
printf '%s' 'https://<stable-backend-public-url>' | \
  npx wrangler pages secret put PANSOU_API_BASE_URL --project-name pansou-bangwo
npm run build
npx wrangler pages deploy dist --project-name pansou-bangwo --branch main
```

后端推荐长期方案优先级：

1. **VPS/云服务器固定公网后端**：安全组放行 `80/443`，用 Nginx/Caddy 反代到 `127.0.0.1:8888`。
2. **固定 Cloudflare Tunnel**：把 `https://<fixed-api-domain>` 绑定到本机 `127.0.0.1:8888`，再写入 `PANSOU_API_BASE_URL`。
3. **临时 tunnel** 只适合验证，不适合长期生产，因为域名和连接可能掉线。

后端运行示例：

```bash
cd backend
PORT=8888 \
CACHE_PATH=$PWD/cache \
ENABLED_PLUGINS=labi,zhizhen,shandian,duoduo,muou \
CHANNELS=tgsearchers7 \
./pansou-bangwo
```

## 验证结果

- 后端 `/api/health` 已返回 `status: ok`
- 前端 dev server 已可访问
- 前端 `/api/health` 代理到后端已验证通过
- 正式站 `https://pansou-bangwo.pages.dev/` 已可访问
- 验收搜索：正式站搜 `四级` 必须显示真实网盘资源；当前返回 8 条 `英语四级 / CET4` 相关盘链，覆盖百度、夸克、移动、迅雷
- 搜索 smoke test 已返回正常 JSON
