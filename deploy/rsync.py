"""通过 SSH/SFTP 将本地 deploy 目录增量上传到远端目录。

本工具不依赖系统 rsync，默认只新增或覆盖远端文件，不删除远端独有文件。
连接信息保存在脚本旁的 .rsync.local.json 中；该文件包含明文密码，必须妥善保护。
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import socket
import stat
import sys
import tempfile
import uuid
from typing import Any, Callable, Iterable, TextIO


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / ".rsync.local.json"
DEFAULT_PORT = 22
SSH_TIMEOUT = 15

EXCLUDED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".pyright",
    ".tox",
    ".nox",
    "runtime",
}
EXCLUDED_FILE_NAMES = {".rsync.local.json"}


class SyncError(RuntimeError):
    """可向使用者展示的同步错误。"""


def _is_reparse_point(path: Path) -> bool:
    """识别 Windows 符号链接和目录联接，避免递归进入外部目录。"""
    try:
        info = os.lstat(path)
    except OSError as error:
        raise SyncError(f"无法读取本地路径：{path}：{error}") from error
    if stat.S_ISLNK(info.st_mode):
        return True
    return bool(getattr(info, "st_file_attributes", 0) & 0x400)


def _is_excluded(relative: PurePosixPath) -> bool:
    """按路径组件过滤部署配置、运行数据和开发机缓存。"""
    parts = relative.parts
    for part in parts:
        if part in EXCLUDED_DIR_NAMES or part.startswith(".build-"):
            return True
    name = relative.name
    if (
        name in EXCLUDED_FILE_NAMES
        or name.startswith(".rsync.local.json.")
        or name.endswith((".pyc", ".pyo"))
    ):
        return True
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return True
    return False


def _walk_local(root: Path) -> list[tuple[PurePosixPath, Path, bool, os.stat_result | None]]:
    """枚举本地目录，不跟随符号链接，结果按路径排序以保持输出稳定。"""
    if _is_reparse_point(root):
        raise SyncError(f"拒绝使用符号链接或目录联接作为本地目录：{root}")
    entries: list[tuple[PurePosixPath, Path, bool, os.stat_result | None]] = []

    def visit(directory: Path, relative_directory: PurePosixPath) -> None:
        try:
            children = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as error:
            raise SyncError(f"无法读取本地目录：{directory}：{error}") from error
        for child in children:
            relative = relative_directory / child.name
            if _is_excluded(relative):
                continue
            child_path = Path(child.path)
            if _is_reparse_point(child_path):
                raise SyncError(f"拒绝同步符号链接或目录联接：{child_path}")
            try:
                info = child.stat(follow_symlinks=False)
            except OSError as error:
                raise SyncError(f"无法读取本地文件：{child_path}：{error}") from error
            if stat.S_ISDIR(info.st_mode):
                entries.append((relative, child_path, True, info))
                visit(child_path, relative)
            elif stat.S_ISREG(info.st_mode):
                entries.append((relative, child_path, False, info))
            else:
                raise SyncError(f"不支持的本地文件类型：{child_path}")

    visit(root, PurePosixPath())
    return entries


def _validate_local_dir(value: str, default: Path) -> Path:
    candidate = Path(value).expanduser() if value else default
    if _is_reparse_point(candidate):
        raise SyncError(f"拒绝使用符号链接或目录联接作为本地目录：{candidate}")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise SyncError(f"本地目录不存在或无法访问：{candidate}：{error}") from error
    if not resolved.is_dir() or _is_reparse_point(resolved):
        raise SyncError(f"本地路径不是普通目录：{resolved}")
    return resolved


def _validate_remote_dir(value: str) -> str:
    candidate = value.strip()
    if not candidate.startswith("/"):
        raise SyncError("远端目录必须是绝对路径，例如 /opt/active-system/deploy")
    candidate = "/" + candidate.lstrip("/")
    path = PurePosixPath(candidate)
    if any(part == ".." for part in path.parts):
        raise SyncError("远端目录不能包含 '..' 路径组件")
    return posixpath.normpath(candidate)


def _load_config(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise SyncError(f"拒绝读取符号链接配置：{path}")
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SyncError(f"配置文件损坏，未覆盖原文件：{path}：{error}") from error
    if not isinstance(data, dict):
        raise SyncError(f"配置文件格式错误，顶层必须是对象：{path}")
    for key in ("host", "username", "password", "local_dir", "remote_dir", "host_key_fingerprint"):
        if key in data and not isinstance(data[key], str):
            raise SyncError(f"配置字段类型错误：{key}")
    if "port" in data and (not isinstance(data["port"], int) or isinstance(data["port"], bool)):
        raise SyncError("配置字段类型错误：port")
    return data


def _save_config(path: Path, data: dict[str, Any]) -> None:
    if path.is_symlink():
        raise SyncError(f"拒绝覆盖符号链接配置：{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != "nt":
            os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        temporary = None
    except OSError as error:
        raise SyncError(f"无法原子保存配置，原文件未覆盖：{path}：{error}") from error
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass


def _prompt_text(label: str, default: str | None, input_func: Callable[[str], str]) -> str:
    prompt = f"{label} [{default}]: " if default else f"{label}: "
    value = input_func(prompt).strip()
    return value or (default or "")


def _prompt_port(default: int, input_func: Callable[[str], str]) -> int:
    value = _prompt_text("SSH 端口", str(default), input_func)
    try:
        port = int(value)
    except ValueError as error:
        raise SyncError("SSH 端口必须是 1 到 65535 的整数") from error
    if not 1 <= port <= 65535:
        raise SyncError("SSH 端口必须是 1 到 65535 的整数")
    return port


def _collect_settings(
    saved: dict[str, Any],
    input_func: Callable[[str], str],
    password_func: Callable[[str], str],
    default_local: Path,
) -> dict[str, Any]:
    host = _prompt_text("服务器 IP 或域名", saved.get("host"), input_func)
    if not host:
        raise SyncError("服务器地址不能为空")
    port = _prompt_port(int(saved.get("port", DEFAULT_PORT)), input_func)
    username = _prompt_text("SSH 用户名", saved.get("username"), input_func)
    if not username:
        raise SyncError("SSH 用户名不能为空")
    identity_same = host == saved.get("host") and port == saved.get("port", DEFAULT_PORT) and username == saved.get(
        "username"
    )
    saved_password = saved.get("password") if identity_same else None
    if saved_password:
        password = password_func("SSH 密码（回车复用已保存密码）：") or saved_password
    else:
        password = password_func("SSH 密码：")
    if not password:
        raise SyncError("SSH 密码不能为空")
    local_default = saved.get("local_dir") or str(default_local)
    local_dir = _validate_local_dir(_prompt_text("本地同步目录", local_default, input_func), default_local)
    remote_default = saved.get("remote_dir")
    remote_dir = _validate_remote_dir(_prompt_text("远端同步目录（绝对路径）", remote_default, input_func))
    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "local_dir": str(local_dir),
        "remote_dir": remote_dir,
        "host_key_fingerprint": saved.get("host_key_fingerprint")
        if host == saved.get("host") and port == saved.get("port", DEFAULT_PORT)
        else "",
        "last_sync_at": saved.get("last_sync_at", ""),
    }


def _fingerprint(key: Any) -> str:
    digest = hashlib.sha256(key.asbytes()).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


def _confirm_host_key(fingerprint: str, input_func: Callable[[str], str]) -> bool:
    answer = input_func(f"首次连接，远端 SSH 主机指纹为 {fingerprint}，确认信任？[y/N]: ").strip().lower()
    return answer in {"y", "yes", "是"}


def _connect(
    settings: dict[str, Any],
    input_func: Callable[[str], str],
    paramiko_module: Any | None = None,
) -> tuple[Any, Any, str]:
    try:
        if paramiko_module is None:
            import paramiko as paramiko_module  # type: ignore[import-not-found]
    except ImportError as error:
        raise SyncError(
            "缺少 Paramiko 依赖，请执行：python -m pip install -r deploy/requirements-rsync.txt"
        ) from error
    transport = None
    try:
        sock = socket.create_connection((settings["host"], settings["port"]), timeout=SSH_TIMEOUT)
        transport = paramiko_module.Transport(sock)
        transport.start_client(timeout=SSH_TIMEOUT)
        fingerprint = _fingerprint(transport.get_remote_server_key())
        expected = settings.get("host_key_fingerprint", "")
        if expected and expected != fingerprint:
            raise SyncError(f"SSH 主机指纹不匹配，已拒绝连接：期望 {expected}，实际 {fingerprint}")
        if not expected and not _confirm_host_key(fingerprint, input_func):
            raise SyncError("未信任远端 SSH 主机，已取消连接")
        try:
            transport.auth_password(settings["username"], settings["password"])
        except Exception as error:
            raise SyncError("SSH 密码认证失败") from error
        if not transport.is_authenticated():
            raise SyncError("SSH 密码认证失败")
        sftp = paramiko_module.SFTPClient.from_transport(transport)
        return transport, sftp, fingerprint
    except SyncError:
        if transport is not None:
            transport.close()
        raise
    except Exception as error:
        if transport is not None:
            transport.close()
        raise SyncError(f"SSH/SFTP 连接失败：{error}") from error


def _remote_attr(sftp: Any, path: str) -> Any | None:
    try:
        return sftp.lstat(path)
    except (FileNotFoundError, OSError) as error:
        if isinstance(error, FileNotFoundError) or getattr(error, "errno", None) in (2, 3):
            return None
        raise SyncError(f"无法读取远端路径：{path}：{error}") from error


def _ensure_remote_dir(sftp: Any, root: str, relative: PurePosixPath, dry_run: bool, known: set[str]) -> int:
    """检查并（在非预览模式）创建目录，返回新建或待建目录数量。"""
    target = posixpath.join(root, relative.as_posix()) if str(relative) != "." else root
    target = posixpath.normpath(target)
    missing = 0
    current = "/"
    parts = PurePosixPath(target).parts
    for part in parts[1:]:
        current = posixpath.join(current, part)
        if current in known:
            continue
        attr = _remote_attr(sftp, current)
        if attr is None:
            missing += 1
            if not dry_run:
                try:
                    sftp.mkdir(current)
                except OSError as error:
                    raise SyncError(f"无法创建远端目录：{current}：{error}") from error
            known.add(current)
            continue
        if stat.S_ISLNK(attr.st_mode):
            raise SyncError(f"拒绝使用远端符号链接目录：{current}")
        if not stat.S_ISDIR(attr.st_mode):
            raise SyncError(f"远端路径不是目录：{current}")
        known.add(current)
    return missing


def _remote_file_action(sftp: Any, path: str, info: os.stat_result, force: bool) -> str:
    attr = _remote_attr(sftp, path)
    if attr is None:
        return "新增"
    if stat.S_ISLNK(attr.st_mode):
        raise SyncError(f"拒绝覆盖远端符号链接：{path}")
    if stat.S_ISDIR(attr.st_mode):
        raise SyncError(f"本地文件与远端目录冲突：{path}")
    if not stat.S_ISREG(attr.st_mode):
        raise SyncError(f"远端路径不是普通文件：{path}")
    if not force and attr.st_size == info.st_size and int(attr.st_mtime) == int(info.st_mtime):
        return "跳过"
    return "覆盖"


class _Progress:
    def __init__(self, output: TextIO, index: int, total: int, relative: PurePosixPath) -> None:
        self.output = output
        self.index = index
        self.total = total
        self.relative = relative
        self.last_percent = -1

    def __call__(self, transferred: int, total: int) -> None:
        percent = int(transferred * 100 / total) if total else 100
        if percent == self.last_percent and transferred != total:
            return
        self.last_percent = percent
        print(f"\r上传 [{self.index}/{self.total}] {self.relative} {percent}%", end="", file=self.output, flush=True)
        if transferred >= total:
            print(file=self.output)


def _upload_file(sftp: Any, local: Path, remote: str, info: os.stat_result, progress: Callable[..., None]) -> None:
    temporary = f"{remote}.rsync-tmp-{uuid.uuid4().hex}"
    try:
        with local.open("rb") as stream:
            sftp.putfo(stream, temporary, file_size=info.st_size, callback=progress)
        sftp.utime(temporary, (int(info.st_atime), int(info.st_mtime)))
        posix_rename = getattr(sftp, "posix_rename", None)
        if not callable(posix_rename):
            raise SyncError("远端 SFTP 不支持原子替换（posix_rename），已保留原文件")
        try:
            posix_rename(temporary, remote)
        except OSError as error:
            raise SyncError(f"远端不支持原子替换，文件未覆盖：{remote}：{error}") from error
    except SyncError:
        try:
            sftp.remove(temporary)
        except OSError:
            pass
        raise
    except Exception as error:
        try:
            sftp.remove(temporary)
        except OSError:
            pass
        raise SyncError(f"上传失败，原文件未覆盖：{remote}：{error}") from error


def sync_directory(
    sftp: Any,
    local_dir: Path,
    remote_dir: str,
    *,
    force: bool = False,
    dry_run: bool = False,
    output: TextIO = sys.stdout,
) -> dict[str, int]:
    """执行一次目录同步，返回新增、覆盖、跳过和目录统计。"""
    entries = _walk_local(local_dir)
    directories = [(relative, info) for relative, _path, is_dir, info in entries if is_dir and info is not None]
    files = [(relative, path, info) for relative, path, is_dir, info in entries if not is_dir and info is not None]
    known: set[str] = set()
    stats = {"新增": 0, "覆盖": 0, "跳过": 0, "目录": 0}
    root_missing = _ensure_remote_dir(sftp, remote_dir, PurePosixPath("."), dry_run, known)
    if root_missing:
        stats["目录"] += root_missing
        print(f"{'预览：' if dry_run else '创建目录：'}{remote_dir}", file=output)
    for relative, _info in directories:
        created = _ensure_remote_dir(sftp, remote_dir, relative, dry_run, known)
        if created:
            stats["目录"] += created
            print(f"{'预览：' if dry_run else '创建目录：'}{relative}", file=output)
    total = len(files)
    for index, (relative, path, info) in enumerate(files, start=1):
        remote = posixpath.join(remote_dir, relative.as_posix())
        action = _remote_file_action(sftp, remote, info, force)
        stats[action] += 1
        if action == "跳过":
            print(f"跳过 [{index}/{total}] {relative}", file=output)
            continue
        if dry_run:
            print(f"预览：{action} [{index}/{total}] {relative}", file=output)
            continue
        print(f"准备{action} [{index}/{total}] {relative}", file=output)
        _upload_file(sftp, path, remote, info, _Progress(output, index, total, relative))
    print(
        f"同步完成：新增 {stats['新增']}，覆盖 {stats['覆盖']}，跳过 {stats['跳过']}，目录 {stats['目录']}",
        file=output,
    )
    return stats


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="通过 SSH/SFTP 增量上传 deploy 目录")
    parser.add_argument("--force", action="store_true", help="忽略大小和修改时间，强制上传文件")
    parser.add_argument("--dry-run", action="store_true", help="只检查并显示变更，不创建目录或上传文件")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH, help=argparse.SUPPRESS)
    return parser


def main(
    argv: Iterable[str] | None = None,
    *,
    input_func: Callable[[str], str] = input,
    password_func: Callable[[str], str] = getpass.getpass,
) -> int:
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        saved = _load_config(args.config)
        settings = _collect_settings(saved, input_func, password_func, SCRIPT_DIR)
        transport, sftp, fingerprint = _connect(settings, input_func)
        try:
            settings["host_key_fingerprint"] = fingerprint
            _save_config(args.config, settings)
            stats = sync_directory(
                sftp,
                Path(settings["local_dir"]),
                settings["remote_dir"],
                force=args.force,
                dry_run=args.dry_run,
            )
            if not args.dry_run:
                settings["last_sync_at"] = datetime.now(timezone.utc).isoformat()
                _save_config(args.config, settings)
            return 0
        finally:
            sftp.close()
            transport.close()
    except (SyncError, KeyboardInterrupt) as error:
        if isinstance(error, KeyboardInterrupt):
            print("已取消。", file=sys.stderr)
        else:
            print(f"同步失败：{error}", file=sys.stderr)
        return 130 if isinstance(error, KeyboardInterrupt) else 1


if __name__ == "__main__":
    sys.exit(main())
