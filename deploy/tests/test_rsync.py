"""SSH/SFTP 同步逻辑测试；使用本地文件系统替身，不连接真实服务器。"""

from __future__ import annotations

import errno
import importlib.util
from io import StringIO
from pathlib import Path, PurePosixPath
import os
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("deploy_rsync", Path(__file__).resolve().parents[1] / "rsync.py")
rsync = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(rsync)


class LocalSftp:
    """将远端 POSIX 路径映射到临时目录的最小 SFTP 替身。"""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.fail_rename = False
        self.mkdir_calls: list[str] = []
        self.rename_calls: list[tuple[str, str]] = []

    def path(self, remote: str) -> Path:
        path = PurePosixPath(remote)
        if not path.is_absolute():
            raise ValueError(remote)
        result = self.root
        for part in path.parts[1:]:
            result /= part
        return result

    def lstat(self, remote: str):
        try:
            return os.lstat(self.path(remote))
        except FileNotFoundError as error:
            raise FileNotFoundError(errno.ENOENT, remote) from error

    def mkdir(self, remote: str) -> None:
        self.path(remote).mkdir()
        self.mkdir_calls.append(remote)

    def putfo(self, stream, remote: str, file_size: int, callback) -> None:
        target = self.path(remote)
        with target.open("wb") as output:
            transferred = 0
            while chunk := stream.read(65536):
                output.write(chunk)
                transferred += len(chunk)
                callback(transferred, file_size)

    def utime(self, remote: str, times: tuple[int, int]) -> None:
        os.utime(self.path(remote), times)

    def posix_rename(self, source: str, target: str) -> None:
        self.rename_calls.append((source, target))
        if self.fail_rename:
            raise OSError(errno.EOPNOTSUPP, "posix rename unavailable")
        os.replace(self.path(source), self.path(target))

    def remove(self, remote: str) -> None:
        try:
            self.path(remote).unlink()
        except FileNotFoundError:
            pass

    def close(self) -> None:
        pass


def write(path: Path, content: str = "content") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class RsyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="deploy-rsync-")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.local = root / "local deploy"
        self.remote_root = root / "remote"
        self.local.mkdir()
        self.remote_root.mkdir()
        self.sftp = LocalSftp(self.remote_root)

    def test_uploads_files_excludes_sensitive_data_and_keeps_remote_only_files(self) -> None:
        write(self.local / "app.txt", "new")
        write(self.local / ".env", "do-not-upload")
        write(self.local / ".env.example", "upload-example")
        write(self.local / "space dir" / "中文.txt", "unicode")
        write(self.local / "runtime" / "database.db", "do-not-upload")
        write(self.local / ".build-stage" / "old.js", "do-not-upload")
        write(self.local / ".rsync.local.json", "do-not-upload")
        write(self.remote_root / "deploy" / "remote-only.txt", "keep")

        stats = rsync.sync_directory(self.sftp, self.local, "/deploy", output=StringIO())

        self.assertEqual(stats["新增"], 3)
        self.assertEqual((self.remote_root / "deploy/app.txt").read_text(encoding="utf-8"), "new")
        self.assertEqual(
            (self.remote_root / "deploy/.env.example").read_text(encoding="utf-8"), "upload-example"
        )
        self.assertEqual((self.remote_root / "deploy/space dir/中文.txt").read_text(encoding="utf-8"), "unicode")
        self.assertFalse((self.remote_root / "deploy/.env").exists())
        self.assertTrue((self.remote_root / "deploy/remote-only.txt").exists())

    def test_second_run_skips_and_force_replaces(self) -> None:
        write(self.local / "app.txt", "same")
        first = rsync.sync_directory(self.sftp, self.local, "/deploy", output=StringIO())
        second = rsync.sync_directory(self.sftp, self.local, "/deploy", output=StringIO())
        forced = rsync.sync_directory(self.sftp, self.local, "/deploy", force=True, output=StringIO())

        self.assertEqual(first["新增"], 1)
        self.assertEqual(second["跳过"], 1)
        self.assertEqual(forced["覆盖"], 1)

    def test_dry_run_does_not_create_remote_paths(self) -> None:
        write(self.local / "app.txt", "new")
        output = StringIO()

        stats = rsync.sync_directory(self.sftp, self.local, "/new/deploy", dry_run=True, output=output)

        self.assertEqual(stats["新增"], 1)
        self.assertFalse((self.remote_root / "new").exists())
        self.assertIn("预览：新增", output.getvalue())
        self.assertEqual(self.sftp.mkdir_calls, [])

    def test_failed_atomic_replace_keeps_original_file(self) -> None:
        write(self.local / "app.txt", "new content")
        write(self.remote_root / "deploy" / "app.txt", "old content")
        self.sftp.fail_rename = True

        with self.assertRaises(rsync.SyncError):
            rsync.sync_directory(self.sftp, self.local, "/deploy", force=True, output=StringIO())

        self.assertEqual((self.remote_root / "deploy/app.txt").read_text(encoding="utf-8"), "old content")
        self.assertEqual(list((self.remote_root / "deploy").glob("*.rsync-tmp-*")), [])

    def test_local_symlink_is_rejected(self) -> None:
        write(self.local / "real.txt", "content")
        try:
            (self.local / "link.txt").symlink_to(self.local / "real.txt")
        except (OSError, NotImplementedError):
            self.skipTest("当前 Windows 环境不允许创建符号链接")

        with self.assertRaises(rsync.SyncError):
            rsync.sync_directory(self.sftp, self.local, "/deploy", output=StringIO())

    def test_remote_symlink_target_is_rejected(self) -> None:
        write(self.local / "app.txt", "content")
        try:
            (self.remote_root / "deploy-target").symlink_to(self.remote_root)
        except (OSError, NotImplementedError):
            self.skipTest("当前 Windows 环境不允许创建符号链接")

        with self.assertRaises(rsync.SyncError):
            rsync.sync_directory(self.sftp, self.local, "/deploy-target", output=StringIO())

    def test_config_is_atomic_and_saved_password_can_be_reused(self) -> None:
        config = Path(self.temp.name) / ".rsync.local.json"
        saved = {
            "host": "192.0.2.10",
            "port": 2222,
            "username": "deploy",
            "password": "secret",
            "local_dir": str(self.local),
            "remote_dir": "/srv/deploy",
            "host_key_fingerprint": "SHA256:known",
        }
        rsync._save_config(config, saved)
        prompts: list[str] = []
        password_prompts: list[str] = []
        values = iter(["", "", "", "", ""])

        settings = rsync._collect_settings(
            rsync._load_config(config),
            lambda prompt: (prompts.append(prompt) or next(values)),
            lambda prompt: (password_prompts.append(prompt) or ""),
            self.local,
        )

        self.assertEqual(settings["password"], "secret")
        self.assertEqual(settings["remote_dir"], "/srv/deploy")
        self.assertTrue(config.exists())
        self.assertEqual(password_prompts, ["SSH 密码（回车复用已保存密码）："])

    def test_invalid_remote_path_is_rejected(self) -> None:
        with self.assertRaises(rsync.SyncError):
            rsync._validate_remote_dir("deploy")

    def test_corrupt_config_is_rejected_without_overwrite(self) -> None:
        config = Path(self.temp.name) / ".rsync.local.json"
        config.write_text("{not-json", encoding="utf-8")

        with self.assertRaises(rsync.SyncError):
            rsync._load_config(config)

        self.assertEqual(config.read_text(encoding="utf-8"), "{not-json")

    def test_file_directory_conflict_is_rejected(self) -> None:
        write(self.local / "app.txt", "content")
        (self.remote_root / "deploy" / "app.txt").mkdir(parents=True)

        with self.assertRaises(rsync.SyncError):
            rsync.sync_directory(self.sftp, self.local, "/deploy", output=StringIO())


if __name__ == "__main__":
    unittest.main()
