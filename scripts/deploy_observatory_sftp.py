"""Deploy standalone Opera+ Observatory beside /atlas, never modifying Atlas files."""
from __future__ import annotations
import os
import posixpath
import stat
from pathlib import Path
from scripts.deploy_atlas_sftp import configuration, make_client, target_path

FILES = ("index.html", "styles.css", "app.js")
SOURCE = Path(__file__).resolve().parents[1] / "observatory"

def publish():
    cfg = configuration()
    client = make_client(cfg)
    try:
        with client.open_sftp() as sftp:
            atlas = target_path(sftp, cfg["target"])
            destination = posixpath.join(posixpath.dirname(atlas), "osservatorio")
            parent = posixpath.dirname(destination)
            info = sftp.stat(parent)
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError("Observatory parent directory not accessible")
            try:
                item = sftp.lstat(destination)
            except OSError:
                sftp.mkdir(destination)
            else:
                if not stat.S_ISDIR(item.st_mode):
                    raise ValueError("Observatory destination is not a directory")
            for name in FILES:
                src = SOURCE / name
                if not src.is_file():
                    raise FileNotFoundError(src)
                sftp.put(str(src), posixpath.join(destination, name), confirm=True)
            print("Published independent Observatory to https://opera.plus/osservatorio/")
    finally:
        client.close()

if __name__ == "__main__":
    publish()
