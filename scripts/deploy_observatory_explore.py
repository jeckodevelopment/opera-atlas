"""Publish only the standalone Explore page, never the Observatory overview."""
from __future__ import annotations

import errno
import posixpath
import stat
import time
from pathlib import Path
from urllib.request import Request, urlopen

from scripts.deploy_atlas_sftp import configuration, make_client, target_path

SOURCE = Path(__file__).resolve().parents[1] / "observatory-explore"
FILES = ("engine.js", "data.js", "analysis.js", "export.js", "report.js",
         "explore.js", "explore.css", "index.html")
PUBLIC = "https://opera.plus/osservatorio/esplora/"


def require_directory(sftp, path, create=False):
    try:
        info = sftp.lstat(path)
    except OSError as error:
        if not create or error.errno != errno.ENOENT:
            raise
        sftp.mkdir(path)
        info = sftp.lstat(path)
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError("Not a real directory: " + path)


def upload(sftp, atlas):
    parent = posixpath.join(posixpath.dirname(atlas), "osservatorio")
    require_directory(sftp, parent)
    destination = posixpath.join(parent, "esplora")
    require_directory(sftp, destination, create=True)
    # Preflight the complete allowlist; reject existing symlinks before writes.
    for name in FILES:
        if not (SOURCE / name).is_file():
            raise FileNotFoundError(name)
        remote = posixpath.join(destination, name)
        try:
            info = sftp.lstat(remote)
        except OSError as error:
            if error.errno != errno.ENOENT:
                raise
        else:
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("Not a regular release file: " + remote)
    # Upload scripts and styles before the entry point.
    for name in FILES:
        remote = posixpath.join(destination, name)
        sftp.put(str(SOURCE / name), remote, confirm=True)
        with sftp.open(remote, "rb") as handle:
            if handle.read() != (SOURCE / name).read_bytes():
                raise ValueError("SFTP verification failed: " + name)


def verify_live():
    for name in FILES:
        url = PUBLIC if name == "index.html" else PUBLIC + name
        expected = (SOURCE / name).read_bytes()
        for attempt in range(3):
            try:
                request = Request(url + "?verify=" + str(time.time_ns()),
                                  headers={"Cache-Control": "no-cache", "User-Agent": "OperaPlusExploreDeploy/1.0"})
                with urlopen(request, timeout=25) as response:
                    if response.status != 200 or response.read() != expected:
                        raise ValueError("Unexpected HTTPS response: " + name)
                break
            except (OSError, ValueError):
                if attempt == 2:
                    raise
                time.sleep(3)


def publish(env=None, connector=make_client):
    cfg = configuration(env)
    client = connector(cfg)
    try:
        with client.open_sftp() as sftp:
            upload(sftp, target_path(sftp, cfg["target"]))
        verify_live()
        print("Published and verified Explore at " + PUBLIC)
    finally:
        client.close()


if __name__ == "__main__":
    publish()
