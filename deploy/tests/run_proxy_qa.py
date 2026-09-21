"""Native Windows proxy regression; explicitly not Linux Docker acceptance."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / f'deploy/runtime/test-qa/proxy-{time.time_ns()}'
NGINX = Path(os.environ.get('QA_NGINX',
    'C:/Users/Administrator/AppData/Local/Temp/active-system-nginx-check/nginx-1.28.3/nginx.exe'))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = os.environ.get('QA_MANIFEST')
    manifest = json.loads(Path(manifest_path).read_text()) if manifest_path else []
    if not manifest:
        print('未提供可用 QA_MANIFEST，本次未执行输入快照校验。', flush=True)
    for item in manifest:
        assert hashlib.sha256((ROOT / item['path']).read_bytes()).hexdigest() == item['sha256'], item
    for app in ('admin', 'screen', 'user'):
        shutil.copytree(ROOT / f'deploy/nginx/html/{app}', OUT / f'html/{app}', dirs_exist_ok=True)
    (OUT / 'logs').mkdir(exist_ok=True)
    (OUT / 'temp').mkdir(exist_ok=True)
    nginx_dir = ROOT / 'deploy/nginx'
    conf = (nginx_dir / 'nginx.conf').read_text(encoding='utf-8')
    client = (nginx_dir / 'conf.d/client.conf').read_text(encoding='utf-8')
    proxy = (nginx_dir / 'conf.d/backend.conf').read_text(encoding='utf-8')
    client = client.replace('include /etc/nginx/conf.d/backend.conf;', proxy)
    client = client.replace('listen 8080;', 'listen 18080;')
    client = client.replace('activate-backend:8000', '127.0.0.1:18081')
    client = client.replace('/usr/share/nginx/html', (OUT / 'html').as_posix())
    cert = NGINX.parent.parent
    tls = f'''server {{ listen 18443 ssl;
        ssl_certificate {cert.as_posix()}/test.crt;
        ssl_certificate_key {cert.as_posix()}/test.key;
        location / {{ proxy_pass http://127.0.0.1:18080;
          proxy_http_version 1.1; proxy_set_header Host $http_host;
          proxy_set_header X-Forwarded-Proto https;
          proxy_set_header Upgrade $http_upgrade;
          proxy_set_header Connection $connection_upgrade;
        }} }}'''
    config = conf.replace('user nginx;', '')
    config = config.replace('/var/log/nginx/', 'logs/').replace('/var/run/nginx.pid', 'logs/nginx.pid')
    config = config.replace('/etc/nginx/mime.types', f'{NGINX.parent.as_posix()}/conf/mime.types')
    config = config.replace('include /etc/nginx/conf.d/client.conf;', client + '\n' + tls)
    (OUT / 'nginx.conf').write_text(config, encoding='utf-8')
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'deploy/backend'),
        DATABASE_PATH=str(OUT / f'qa-{int(time.time())}.db'), MEDIA_ROOT=str(OUT / 'media'),
        JWT_SECRET='qa-only-secret-at-least-thirty-two-bytes', SUPERUSER_USERNAME='qaadmin',
        SUPERUSER_PASSWORD='qa-test-password-123', LOTTERY_SECURITY_CODE='qa654321',
        APP_CORS_ORIGINS='', APP_ENV='test', DANMAKU_TOKEN_SECRET='qa-only-danmaku-token')
    with (OUT / 'backend.log').open('w') as backend_log, (OUT / 'nginx.log').open('w') as nginx_log:
        backend = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app',
            '--host', '127.0.0.1', '--port', '18081'], cwd=OUT, env=env,
            stdout=backend_log, stderr=subprocess.STDOUT)
        nginx = None
        try:
            subprocess.run([str(NGINX), '-p', OUT.as_posix() + '/', '-c', 'nginx.conf', '-t'], check=True)
            nginx = subprocess.Popen([str(NGINX), '-p', OUT.as_posix() + '/', '-c', 'nginx.conf'],
                cwd=OUT, stdout=nginx_log, stderr=subprocess.STDOUT)
            import httpx
            for _ in range(40):
                try:
                    if httpx.get('http://127.0.0.1:18080/api/v1/health').status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(.5)
            subprocess.run(['node', str(ROOT / 'deploy/tests/proxy_browser.cjs'), str(OUT)], check=True)
        finally:
            if nginx:
                subprocess.run([str(NGINX), '-p', OUT.as_posix() + '/', '-c', 'nginx.conf', '-s', 'quit'])
                nginx.wait(timeout=10)
            backend.terminate()
            backend.wait(timeout=10)
    for item in manifest:
        assert hashlib.sha256((ROOT / item['path']).read_bytes()).hexdigest() == item['sha256'], item


if __name__ == '__main__':
    main()
