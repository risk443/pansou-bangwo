const DEFAULT_BACKEND = ''

function corsHeaders(extra = {}) {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    ...extra,
  }
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: corsHeaders({ 'Content-Type': 'application/json; charset=utf-8' }),
  })
}

function joinUrl(base, pathname, search) {
  const cleanBase = (base || '').replace(/\/$/, '')
  return `${cleanBase}${pathname}${search || ''}`
}

function getBackend(context) {
  return (context.env.PANSOU_API_BASE_URL || context.env.BACKEND_URL || DEFAULT_BACKEND).trim().replace(/\/$/, '')
}

export async function proxyRequest(context) {
  const url = new URL(context.request.url)
  const backend = getBackend(context)

  if (!backend) {
    if (url.pathname === '/api/health') {
      return json({
        status: 'frontend_online_backend_pending',
        plugins_enabled: false,
        plugin_count: 0,
        plugins: [],
        channels: [],
        auth_enabled: false,
        message: 'Cloudflare Pages 前端已上线；PanSou Go 后端还未配置公网地址。',
      })
    }

    return json({
      code: 503,
      message: 'PanSou 后端公网地址未配置。请设置 Cloudflare Pages 环境变量 PANSOU_API_BASE_URL。',
      data: null,
    }, 503)
  }

  const target = joinUrl(backend, url.pathname, url.search)
  const headers = new Headers(context.request.headers)
  headers.set('Host', new URL(backend).host)

  const init = {
    method: context.request.method,
    headers,
    body: ['GET', 'HEAD'].includes(context.request.method) ? undefined : context.request.body,
    redirect: 'manual',
  }

  try {
    const response = await fetch(target, init)
    const outHeaders = new Headers(response.headers)
    for (const [key, value] of Object.entries(corsHeaders())) outHeaders.set(key, value)
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: outHeaders,
    })
  } catch (error) {
    return json({
      code: 502,
      message: `无法连接 PanSou 后端：${error && error.message ? error.message : String(error)}`,
      data: null,
    }, 502)
  }
}

export function handleOptions() {
  return new Response(null, {
    status: 204,
    headers: corsHeaders(),
  })
}
