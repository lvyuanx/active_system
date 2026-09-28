"""在仓库外验证 Compose 解析；不连接 daemon，不读取真实 .env。"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

DEPLOY = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("docker"), "需要 Docker Compose CLI")
class ComposeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="activate-compose-")
        self.addCleanup(self.temp.cleanup)
        self.deploy = Path(self.temp.name) / "deploy"
        shutil.copytree(DEPLOY, self.deploy, ignore=shutil.ignore_patterns(
            "runtime", "workflow", "tests", ".build-*", ".env", "__pycache__",
        ))
        self.env = {key: value for key, value in os.environ.items() if key not in (
            "SUPERUSER_PASSWORD", "JWT_SECRET", "LOTTERY_SECURITY_CODE", "SUPERUSER_USERNAME",
            "DANMAKU_TOKEN_SECRET", "APP_CORS_ORIGINS",
        ) and not key.startswith("COMPOSE_")}
        (self.deploy / ".env").write_text(
            "SUPERUSER_PASSWORD=test-password-only\n"
            "JWT_SECRET=test-only-secret-at-least-32-characters\nLOTTERY_SECURITY_CODE=test123\n",
            encoding="utf-8",
        )

    def config(self):
        return subprocess.run(
            ["docker", "compose", "--env-file", ".env", "config", "--format", "json"],
            cwd=self.deploy, env=self.env, capture_output=True, text=True, encoding="utf-8",
        )

    def test_portable_paths_ports_network_and_mounts(self):
        self.assertFalse((self.deploy / "runtime/data").exists())
        result = self.config()
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads(result.stdout)
        services = config["services"]
        self.assertEqual(set(services), {"activate-backend", "activate-nginx"})
        for name, internal in (("activate-backend", "8000"), ("activate-nginx", "8080")):
            service = services[name]
            self.assertEqual(service["container_name"], name)
            self.assertNotIn("ports", service)
            self.assertEqual(service["expose"], [internal])
            self.assertIn("open-getaway-network", service["networks"])
            self.assertTrue(Path(service["build"]["context"]).is_relative_to(self.deploy))
            for mount in service["volumes"]:
                self.assertTrue(Path(mount["source"]).is_relative_to(self.deploy))
                if mount["target"] != "/app/data":
                    self.assertTrue(mount["read_only"])
                    self.assertFalse(mount["bind"]["create_host_path"])
                else:
                    self.assertFalse(mount.get("read_only", False))
                    # 部分 Compose 版本在 config 输出中省略值为 true 的默认字段。
                    self.assertTrue(mount.get("bind", {}).get("create_host_path", True))
        network = config["networks"]["open-getaway-network"]
        self.assertEqual(network["name"], "open-getaway-network")
        self.assertEqual(network["driver"], "bridge")
        self.assertEqual(services["activate-nginx"]["depends_on"]["activate-backend"]["condition"], "service_healthy")

    def test_missing_credentials_refuse_start(self):
        (self.deploy / ".env").write_text("SUPERUSER_PASSWORD=\n", encoding="utf-8")
        result = self.config()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SUPERUSER_PASSWORD", result.stderr)


if __name__ == "__main__":
    unittest.main()
