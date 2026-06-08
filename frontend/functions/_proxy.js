const DEFAULT_BACKEND = 'http://127.0.0.1:8888'

function joinUrl(base, pathname, search) {
  const cleanBase = (base || DEFAULT_BACKEND).replace(/\/$/, '')
  return `${cleanBase}${pathname}${search || ''}`
}

export async function proxyRequest(context) {
  const url = new URL(context.request.url)
  const backend = context.env.PANSOU_API_BASE_URL || context.env.BACKEND_URL || DEFAULT_BACKEND
  const target = joinUrl(backend, url.pathname, url.search)

  const headers = new Headers(context.request.headers)
  headers.set('Host', new URL(backend).host)

  const init = {
    method: context.request.method,
    headers,
    body: ['GET', 'HEAD'].includes(context.request.method) ? undefined : context.request.body,
    redirect: 'manual',
  }

  const response = await fetch(target, init)
  const outHeaders = new Headers(response.headers)
  outHeaders.set('Access-Control-Allow-Origin', '*')
  outHeaders.set('Access-Control-Allow-Methods', 'GET,POST,PUT,PATCH,DELETE,OPTIONS')
  outHeaders.set('Access-Control-Allow-Headers', 'Content-Type,Authorization')
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: outHeaders,
  })
}

export function handleOptions() {
  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    },
  })
}
