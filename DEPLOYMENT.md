# PanSou Bangwo 部署方案

## 当前线上结构

- GitHub：托管代码仓库 `risk443/pansou-bangwo`
- Cloudflare Pages：托管前端静态站点
  - 线上地址：https://pansou-bangwo.pages.dev/
- PanSou Go 后端：负责实际搜索 API
  - 本地服务端口：`127.0.0.1:8888`
  - Pages Functions 通过环境变量 `PANSOU_API_BASE_URL` 代理到公网后端

## 为什么不能只用 GitHub 解决

GitHub 可以解决：

1. 代码托管；
2. GitHub Actions 自动构建；
3. 触发 Cloudflare Pages/Vercel 等静态前端部署；
4. 保存后端部署配置、Dockerfile、说明文档。

但 PanSou 搜索依赖 Go 后端常驻进程。GitHub Pages 只能托管静态文件，GitHub Actions 也不是常驻服务器，任务会超时退出，所以不能作为稳定线上后端。

因此正确架构是：

```text
GitHub 仓库
  ├─ 前端源码 -> Cloudflare Pages -> https://pansou-bangwo.pages.dev/
  └─ 后端源码/二进制/Docker 配置 -> 稳定后端运行环境

浏览器
  -> https://pansou-bangwo.pages.dev/
  -> /api/search
  -> Cloudflare Pages Functions
  -> PANSOU_API_BASE_URL
  -> PanSou Go 后端
```

## 当前临时可用方案

当前为了先让线上能搜，使用本机 PanSou 后端 + 临时公网隧道：

- 后端本机服务：`127.0.0.1:8888`
- Cloudflare Pages 环境变量：`PANSOU_API_BASE_URL=<临时公网后端地址>`
- 线上已验证：
  - `/api/health` 返回 `status: ok`
  - `/api/search?kw=三体&src=plugin&res=results` 返回 `code: 0` 和搜索结果

为了减少临时隧道掉线影响，已增加 watchdog：

- 脚本：`scripts/pansou-watchdog.py`
- Hermes 定时任务：`pansou-bangwo-watchdog`
- 频率：每 5 分钟
- 行为：
  1. 检查本地 Go 后端；
  2. 检查线上 Pages 搜索；
  3. 如隧道失效，尝试重新创建公网隧道；
  4. 如公网地址变化，自动更新 Cloudflare Pages 的 `PANSOU_API_BASE_URL` 并重新部署；
  5. 正常时静默，异常/恢复时提醒。

## 长期稳定方案优先级

### 方案 A：当前服务器开放公网端口或 Nginx 反代，推荐

当前服务器有公网出口 IP：`1.14.94.104`，但外网访问 `1.14.94.104:8888` 超时，说明云厂商安全组/入站规则未放行。

如果能登录云服务器控制台，放行入站端口或绑定域名后，最稳做法：

1. 放行 TCP `8888`，或只放行 `80/443`；
2. 用 Nginx/Caddy 反代到 `127.0.0.1:8888`；
3. 配 HTTPS 域名，例如 `https://pansou-api.your-domain.com`；
4. 更新 Cloudflare Pages 环境变量：
   ```text
   PANSOU_API_BASE_URL=https://pansou-api.your-domain.com
   ```
5. 重新部署 Pages；
6. 验证：
   ```bash
   curl https://pansou-bangwo.pages.dev/api/health
   curl 'https://pansou-bangwo.pages.dev/api/search?kw=三体&src=plugin&res=results'
   ```

### 方案 B：Cloudflare Tunnel 固定隧道，推荐

优点：不用开放服务器端口，稳定，适合当前结构。

当前 Cloudflare token 可以部署 Pages，但没有 Tunnel 权限。需要 Cloudflare API Token 增加：

```text
Account > Cloudflare Tunnel > Edit
```

然后可创建固定 Tunnel，把 `https://pansou-api.<domain>` 指到本机 `127.0.0.1:8888`。

### 方案 C：容器平台运行后端

把后端部署到 Render/Railway/Fly.io/Koyeb 等能常驻运行 Go/Docker 的平台。

要求：

- 支持常驻 HTTP 服务；
- 暴露公网 HTTPS 地址；
- 能设置环境变量：
  - `PORT=8888` 或平台提供的 `$PORT`
  - `CHANNELS=tgsearchers7`
  - `ENABLED_PLUGINS=labi,zhizhen,shandian,duoduo,muou`
  - `CACHE_PATH=/tmp/pansou-cache` 或持久盘路径

拿到公网后端地址后，设置：

```text
PANSOU_API_BASE_URL=https://你的后端公网地址
```

## 本地后端启动命令

```bash
cd /home/ubuntu/pansou-bangwo/backend
PORT=8888 \
CACHE_PATH=$PWD/cache \
ENABLED_PLUGINS=labi,zhizhen,shandian,duoduo,muou \
CHANNELS=tgsearchers7 \
./pansou-bangwo
```

## Cloudflare Pages 更新后端地址

```bash
cd /home/ubuntu/pansou-bangwo/frontend
printf '%s' 'https://你的后端公网地址' \
  | npx wrangler pages secret put PANSOU_API_BASE_URL --project-name pansou-bangwo

npx wrangler pages deploy dist --project-name pansou-bangwo --branch main
```

## 验证标准

```bash
curl https://pansou-bangwo.pages.dev/api/health
curl 'https://pansou-bangwo.pages.dev/api/search?kw=三体&src=plugin&res=results'
```

成功标准：

- health：`status=ok`
- search：`code=0` 且返回结果数大于 0
