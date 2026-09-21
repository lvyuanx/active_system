"""产物发布与失败恢复测试，不运行真实 pnpm，不访问实际运行数据。"""

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("deploy_build", Path(__file__).resolve().parents[1] / "build.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def write(path: Path, content: str = "test") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def snapshot(path: Path) -> dict[str, bytes]:
    return {str(item.relative_to(path)): item.read_bytes() for item in path.rglob("*") if item.is_file()}


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.deploy = self.root / "deploy"
        self.deploy.mkdir()
        write(self.root / "apps/backend/app/main.py", "app = None\n")
        write(self.root / "apps/backend/migrations/.gitkeep", "")
        write(self.root / "apps/backend/pyproject.toml", '[project]\ndependencies = ["fastapi>=0.115"]\n')
        for relative in (".env", "nginx/nginx.conf", "runtime/data/active_system.db", "runtime/data/media/a.png"):
            write(self.deploy / relative, "preserve")

    def frontend(self, root, stage, pnpm):
        for app in builder.WEB_APPS:
            write(stage / f"nginx/html/{app}/index.html", f"/{app}/")

    def build(self):
        with patch.object(builder, "find_pnpm", return_value="pnpm"), \
                patch.object(builder, "stage_frontend", side_effect=self.frontend):
            builder.build(self.root, self.deploy)

    def test_repeat_build_removes_stale_outputs_preserves_settings_and_data(self):
        before = snapshot(self.deploy)
        self.build()
        write(self.deploy / "nginx/html/admin/stale.js")
        write(self.deploy / "backend/app/removed.py")
        self.build()
        self.assertFalse((self.deploy / "nginx/html/admin/stale.js").exists())
        self.assertFalse((self.deploy / "backend/app/removed.py").exists())
        after = snapshot(self.deploy)
        for name, content in before.items():
            self.assertEqual(after[name], content)
        self.assertEqual((self.deploy / "backend/requirements.txt").read_text(), "fastapi>=0.115\n")

    def test_frontend_failure_leaves_previous_deployment_intact(self):
        self.build()
        before = snapshot(self.deploy)
        with patch.object(builder, "find_pnpm", return_value="pnpm"), \
                patch.object(builder, "stage_frontend", side_effect=subprocess.CalledProcessError(1, "pnpm")):
            with self.assertRaises(subprocess.CalledProcessError):
                builder.build(self.root, self.deploy)
        self.assertEqual(snapshot(self.deploy), before)

    def test_publish_failure_restores_all_previous_outputs(self):
        self.build()
        before = snapshot(self.deploy)
        rename = Path.rename
        failed = False

        def fail_once(source, destination):
            nonlocal failed
            if not failed and str(source).endswith("requirements.txt") and "previous" not in str(destination):
                failed = True
                raise OSError("模拟发布阶段文件占用")
            return rename(source, destination)

        with patch.object(Path, "rename", fail_once):
            with self.assertRaises(OSError):
                self.build()
        self.assertTrue(failed)
        self.assertEqual(snapshot(self.deploy), before)

    def test_backend_excludes_secrets_cache_and_data(self):
        app = self.root / "apps/backend/app"
        for name in (".env", ".env.production", "__pycache__/a.pyc", "data/test.db", "media/a.png", "key.pem"):
            write(app / name)
        stage = self.root / "stage"
        builder.stage_backend(self.root, stage)
        self.assertEqual(set(snapshot(stage / "backend/app")), {"main.py"})

    def test_frontend_commands_use_three_web_apps_and_portable_urls(self):
        calls = []
        stage = self.root / "stage"

        def fake_run(command, cwd, env=None):
            calls.append((command, env))
            if "vite" in command:
                output = Path(command[command.index("--outDir") + 1])
                write(output / "index.html")

        with patch.object(builder, "run", side_effect=fake_run):
            builder.stage_frontend(self.root, stage, "pnpm")
        self.assertIn("--frozen-lockfile", calls[0][0])
        self.assertEqual(len(calls), 7)
        self.assertNotIn("danmaku-desktop", str(calls))
        for command, env in calls[1:]:
            self.assertEqual(env["VITE_API_BASE_URL"], "/api/v1")
        for app, (command, _) in zip(builder.WEB_APPS, calls[2::2]):
            self.assertIn(f"--base=/{app}/", command)


if __name__ == "__main__":
    unittest.main()
