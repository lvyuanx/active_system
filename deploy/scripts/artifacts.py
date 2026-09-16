"""Container-side archive and resolved Compose handling; no host Python is required."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile


def validate_archive(archive):
    for member in archive.getmembers():
        path = PurePosixPath(member.name)
        unsafe = path.is_absolute() or ".." in path.parts or "\\" in member.name or ":" in member.name
        if unsafe or not (member.isfile() or member.isdir()):
            raise ValueError("Archive contains unsupported paths or file types")


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def backup():
    output = Path("/output")
    partial = output / "data.tar.gz.partial"
    with tarfile.open(partial, "w:gz") as archive:
        archive.add("/source", arcname=".", recursive=True)
    with tarfile.open(partial, "r:gz") as archive:
        validate_archive(archive)
        for member in archive.getmembers():
            if member.isfile():
                with archive.extractfile(member) as source:
                    while source.read(1024 * 1024):
                        pass
    (output / "data.sha256").write_text(digest(partial) + "\n")
    partial.rename(output / "data.tar.gz")


def pin(record):
    path = record / "compose.json"
    config = json.loads(path.read_text())
    for service in ("backend", "nginx"):
        config["services"][service]["image"] = (record / f"{service}-image").read_text().strip()
        config["services"][service].pop("build", None)
    path.write_text(json.dumps(config, indent=2) + "\n")


def restore(record, target):
    archive_path = record / "data.tar.gz"
    if digest(archive_path) != (record / "data.sha256").read_text().strip():
        raise ValueError("Backup SHA-256 mismatch")
    if any(target.iterdir()):
        raise ValueError("Recovery target must be empty")
    with tarfile.open(archive_path, "r:gz") as archive:
        validate_archive(archive)
        # Copy only validated regular files into a new tree; also supports early Python 3.11 patch releases.
        for member in archive.getmembers():
            destination = target.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, destination.open("xb") as output:
                    shutil.copyfileobj(source, output)


def recovery_config(record, host_data_path):
    path = record / "compose.json"
    config = json.loads(path.read_text())
    mounts = config["services"]["backend"]["volumes"]
    data_mounts = [mount for mount in mounts if mount.get("target") == "/app/data"]
    if len(data_mounts) != 1:
        raise ValueError("Expected exactly one data mount")
    data_mounts[0]["source"] = host_data_path
    path.write_text(json.dumps(config, indent=2) + "\n")


if __name__ == "__main__":
    os.umask(0o077)
    command = sys.argv[1]
    if command == "backup":
        backup()
    elif command == "pin":
        pin(Path("/runtime") / sys.argv[2])
    elif command == "restore":
        restore(Path("/runtime") / sys.argv[2], Path("/runtime") / sys.argv[3])
    elif command == "config":
        recovery_config(Path("/runtime") / sys.argv[2], sys.argv[3])
    else:
        raise ValueError("Unknown operation")
