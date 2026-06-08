import { handleOptions, proxyRequest } from '../_proxy.js'

export async function onRequest(context) {
  if (context.request.method === 'OPTIONS') return handleOptions()
  return proxyRequest(context)
}
