#!/usr/bin/env python3
"""Watch PanSou backend + public tunnel and keep Cloudflare Pages proxy pointed at a working backend.

This is a practical bridge until a fixed backend runtime is available.
It:
  1. Ensures local PanSou backend answers on 127.0.0.1:8888.
  2. Ensures an ssh localhost.run tunnel is running.
  3. Extracts the current https://*.lhr.life URL from tunnel logs.
  4. Verifies the public backend health/search endpoints.
  5. If the URL changed, updates Cloudflare Pages secret PANSOU_API_BASE_URL and redeploys.
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ROOT = Path('/home/ubuntu/pansou-bangwo')
FRONTEND = ROOT / 'frontend'
STATE = ROOT / '.state'
STATE.mkdir(exist_ok=True)
TUNNEL_LOG = STATE / 'localhost-run-tunnel.log'
PID_FILE = STATE / 'localhost-run-tunnel.pid'
CURRENT_URL_FILE = STATE / 'backend-public-url.txt'
TOKEN_FILE = Path('/home/ubuntu/.hermes/profiles/wx_hu/state/cloudflare_api_token.txt')
PROJECT = 'pansou-bangwo'
LOCAL_BACKEND = 'http://127.0.0.1:8888'


def run(cmd, cwd=ROOT, env=None, timeout=120, check=False):
    merged = os.environ.copy()
    if env:
        merged.update(env)
    p = subprocess.run(cmd, cwd=str(cwd), env=merged, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError(f"command failed {cmd}:\n{p.stdout}")
    return p.returncode, p.stdout


def http_json(url, timeout=20):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 pansou-watchdog'})
    with urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return r.status, json.loads(raw)


def local_backend_ok():
    try:
        status, data = http_json(f'{LOCAL_BACKEND}/api/health', 8)
        return status == 200 and data.get('status') == 'ok'
    except Exception:
        return False


def start_backend_if_needed():
    if local_backend_ok():
        return True
    backend_bin = ROOT / 'backend' / 'pansou-bangwo'
    if not backend_bin.exists():
        print('backend binary missing:', backend_bin)
        return False
    log = STATE / 'backend.log'
    env = os.environ.copy()
    env.update({
        'PORT': '8888',
        'CACHE_PATH': str(ROOT / 'backend' / 'cache'),
        'ENABLED_PLUGINS': 'labi,zhizhen,shandian,duoduo,muou',
        'CHANNELS': 'tgsearchers7',
    })
    with log.open('ab') as f:
        subprocess.Popen([str(backend_bin)], cwd=str(ROOT / 'backend'), env=env,
                         stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(15):
        time.sleep(1)
        if local_backend_ok():
            return True
    return False


def pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def tunnel_running():
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
    except Exception:
        return False
    return pid_running(pid)


def start_tunnel():
    if tunnel_running():
        return
    # truncate old log so URL extraction gets the fresh assigned URL
    TUNNEL_LOG.write_text('')
    cmd = [
        'ssh',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        '-o', 'ServerAliveInterval=10',
        '-R', '80:127.0.0.1:8888',
        'nokey@localhost.run',
    ]
    with TUNNEL_LOG.open('ab') as f:
        p = subprocess.Popen(cmd, cwd=str(ROOT), stdout=f, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True)
    PID_FILE.write_text(str(p.pid))


def extract_tunnel_url():
    text = TUNNEL_LOG.read_text(errors='ignore') if TUNNEL_LOG.exists() else ''
    matches = re.findall(r'https://[a-zA-Z0-9.-]+\.lhr\.life', text)
    return matches[-1] if matches else None


def public_backend_ok(base: str):
    try:
        st, health = http_json(f'{base}/api/health', 20)
        if st != 200 or health.get('status') != 'ok':
            return False
        st, search = http_json(f'{base}/api/search?kw=%E4%B8%89%E4%BD%93&src=plugin&res=results', 45)
        data = search.get('data')
        results = data.get('results') if isinstance(data, dict) else data
        return st == 200 and search.get('code') == 0 and bool(results)
    except Exception as e:
        print('public check failed:', repr(e))
        return False


def current_pages_ok():
    try:
        st, health = http_json('https://pansou-bangwo.pages.dev/api/health', 25)
        if st != 200 or health.get('status') != 'ok':
            return False
        st, search = http_json('https://pansou-bangwo.pages.dev/api/search?kw=%E4%B8%89%E4%BD%93&src=plugin&res=results', 60)
        data = search.get('data')
        results = data.get('results') if isinstance(data, dict) else data
        return st == 200 and search.get('code') == 0 and bool(results)
    except Exception as e:
        print('pages check failed:', repr(e))
        return False


def update_cloudflare_url(base: str):
    if not TOKEN_FILE.exists():
        raise RuntimeError('Cloudflare token file missing')
    token = TOKEN_FILE.read_text().strip()
    env = {'CLOUDFLARE_API_TOKEN': token}
    # wrangler pages secret put reads stdin, so use subprocess.run(input=...).
    p = subprocess.run(['npx', 'wrangler', 'pages', 'secret', 'put', 'PANSOU_API_BASE_URL', '--project-name', PROJECT],
                       input=base, cwd=str(FRONTEND), env={**os.environ, **env}, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
    if p.returncode != 0:
        raise RuntimeError('secret update failed:\n' + p.stdout)
    p = subprocess.run(['npx', 'wrangler', 'pages', 'deploy', 'dist', '--project-name', PROJECT, '--branch', 'main'],
                       cwd=str(FRONTEND), env={**os.environ, **env}, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
    if p.returncode != 0:
        raise RuntimeError('pages deploy failed:\n' + p.stdout)
    CURRENT_URL_FILE.write_text(base + '\n')


def main():
    if not start_backend_if_needed():
        print('ERROR backend not healthy')
        return 2
    if current_pages_ok():
        print('OK pages search works')
        return 0
    start_tunnel()
    url = None
    for _ in range(60):
        url = extract_tunnel_url()
        if url and public_backend_ok(url):
            break
        time.sleep(2)
    else:
        print('ERROR no working tunnel URL')
        return 3
    old = CURRENT_URL_FILE.read_text().strip() if CURRENT_URL_FILE.exists() else ''
    if old != url or not current_pages_ok():
        print('updating Cloudflare Pages backend URL to', url)
        update_cloudflare_url(url)
        time.sleep(8)
    if current_pages_ok():
        print('OK pages search restored via', url)
        return 0
    print('ERROR pages still not healthy after update')
    return 4


if __name__ == '__main__':
    raise SystemExit(main())
