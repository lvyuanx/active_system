"""在开发机生成可独立复制的部署产物；不启动容器或修改运行数据。"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib

DEPLOY = Path(__file__).resolve().parent
ROOT = DEPLOY.parent
WEB_APPS = ("admin", "screen", "user")
OUTPUTS = ("backend/app", "backend/migrations", "backend/requirements.txt", "nginx/html")
IGNORE = shutil.ignore_patterns(
    "__pycache__", "*.pyc", "*.pyo", ".env", ".env.*", ".venv", "venv", "node_modules",
    ".pytest_cache", "*.egg-info", "*.db", "*.db-*", "*.sqlite*", "*.log", "*.pem", "*.key",
    "data", "media", "uploads", "AGENTS.md",
)


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print("执行：" + " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def find_pnpm(root: Path) -> str:
    expected = json.loads((root / "package.json").read_text(encoding="utf-8"))["packageManager"]
    pnpm = shutil.which("pnpm.cmd" if os.name == "nt" else "pnpm")
    if not pnpm or not shutil.which("node"):
        raise RuntimeError(f"请安装 Node.js 和 {expected} 后再打包")
    version = subprocess.check_output([pnpm, "--version"], cwd=root, text=True).strip()
    if f"pnpm@{version}" != expected:
        raise RuntimeError(f"项目要求 {expected}，当前为 pnpm@{version}")
    return pnpm


def stage_backend(root: Path, stage: Path) -> None:
    source = root / "apps/backend"
    target = stage / "backend"
    target.mkdir(parents=True)
    for name in ("app", "migrations"):
        shutil.copytree(source / name, target / name, ignore=IGNORE)
    with (source / "pyproject.toml").open("rb") as stream:
        dependencies = tomllib.load(stream)["project"]["dependencies"]
    (target / "requirements.txt").write_text("\n".join(dependencies) + "\n", encoding="utf-8")
    if not (target / "app/main.py").is_file():
        raise RuntimeError("后端产物缺少 app/main.py")


def stage_frontend(root: Path, stage: Path, pnpm: str) -> None:
    filters = [arg for app in WEB_APPS for arg in ("--filter", f"@active/{app}-web")]
    run([pnpm, "install", "--frozen-lockfile", *filters], root)
    # 部署包固定使用同源地址，避免开发机的 VITE 环境覆盖可移植部署约定。
    env = dict(os.environ, VITE_API_BASE_URL="/api/v1",
               VITE_SCREEN_WEB_BASE_URL="/screen/", VITE_USER_WEB_BASE_URL="/user/")
    for app in WEB_APPS:
        prefix = [pnpm, "--filter", f"@active/{app}-web", "exec"]
        run([*prefix, "vue-tsc", "--noEmit"], root, env)
        output = stage / "nginx/html" / app
        run([*prefix, "vite", "build", f"--base=/{app}/", "--outDir", str(output)], root, env)
        if not (output / "index.html").is_file():
            raise RuntimeError(f"前端产物缺少 {app}/index.html")


def publish(stage: Path, deploy: Path) -> None:
    """同一文件系统内更名；更新失败时恢复所有已移动的产物。"""
    for relative in OUTPUTS:
        target = deploy / relative
        if target.is_symlink() or target.parent.is_symlink():
            raise RuntimeError(f"拒绝替换符号链接产物：{target}")
        if not (stage / relative).exists():
            raise RuntimeError(f"暂存产物缺失：{relative}")
    backups: list[tuple[Path, Path]] = []
    installed: list[tuple[Path, Path]] = []
    try:
        for relative in OUTPUTS:
            target, source = deploy / relative, stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                backup = stage / "previous" / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                target.rename(backup)
                backups.append((backup, target))
            source.rename(target)
            installed.append((target, source))
    except BaseException:
        for target, source in reversed(installed):
            target.rename(source)
        for backup, target in reversed(backups):
            backup.rename(target)
        raise


def build(root: Path = ROOT, deploy: Path = DEPLOY) -> None:
    pnpm = find_pnpm(root)
    stage = Path(tempfile.mkdtemp(prefix=".build-", dir=deploy))
    try:
        stage_backend(root, stage)
        stage_frontend(root, stage, pnpm)
        publish(stage, deploy)
    except BaseException:
        # 更名回滚自身失败时保留旧文件供人工恢复，不在 finally 中删除备份。
        if any((stage / "previous" / relative).exists() for relative in OUTPUTS):
            print(f"打包失败，备份或暂存文件保留在：{stage}", file=sys.stderr)
        else:
            shutil.rmtree(stage)
        raise
    else:
        shutil.rmtree(stage)
    print(f"打包完成：{deploy}\n复制整个目录到服务器，配置 .env 后运行：\n"
          "docker compose --env-file .env up -d --build --wait", flush=True)


if __name__ == "__main__":
    try:
        build()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"打包失败：{error}", file=sys.stderr)
        sys.exit(1)
