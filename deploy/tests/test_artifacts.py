import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("artifacts", Path(__file__).parents[1] / "scripts/artifacts.py")
artifacts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(artifacts)


class ArchiveTests(unittest.TestCase):
    def test_restore_and_reject_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.mkdir()
            path = root / "data.tar.gz"
            with tarfile.open(path, "w:gz") as archive:
                member = tarfile.TarInfo("media/image.png")
                member.size = 3
                archive.addfile(member, io.BytesIO(b"png"))
            (root / "data.sha256").write_text(artifacts.digest(path))
            artifacts.restore(root, target)
            self.assertEqual((target / "media/image.png").read_bytes(), b"png")
            with self.assertRaisesRegex(ValueError, "empty"):
                artifacts.restore(root, target)

    def test_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data.tar.gz").write_bytes(b"broken")
            (root / "data.sha256").write_text("wrong")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                artifacts.restore(root, root)

    def test_unsafe_paths_and_symlinks(self):
        for name, kind in [("../escape", tarfile.REGTYPE), ("/absolute", tarfile.REGTYPE),
                           ("link", tarfile.SYMTYPE)]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "archive.tar"
                with tarfile.open(path, "w") as archive:
                    member = tarfile.TarInfo(name)
                    member.type = kind
                    member.linkname = "/outside"
                    archive.addfile(member)
                with tarfile.open(path) as archive, self.assertRaises(ValueError):
                    artifacts.validate_archive(archive)


if __name__ == "__main__":
    unittest.main()
