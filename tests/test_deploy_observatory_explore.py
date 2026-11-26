"""Prove the independent deploy cannot touch the Observatory overview."""
import errno
import io
import stat
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts import deploy_observatory_explore as deploy


class FakeSFTP:
    def __init__(self):
        self.dirs = {"/www/osservatorio"}
        self.files = {"/www/osservatorio/index.html": b"unchanged",
                      "/www/atlas/index.html": b"unchanged"}
        self.links = set()
        self.writes = []

    def lstat(self, path):
        if path in self.links:
            return SimpleNamespace(st_mode=stat.S_IFLNK)
        if path in self.dirs:
            return SimpleNamespace(st_mode=stat.S_IFDIR)
        if path in self.files:
            return SimpleNamespace(st_mode=stat.S_IFREG)
        raise FileNotFoundError(errno.ENOENT, path)

    def mkdir(self, path):
        self.dirs.add(path)

    def put(self, local, remote, confirm=True):
        self.writes.append(remote)
        self.files[remote] = Path(local).read_bytes()

    def open(self, path, mode):
        return io.BytesIO(self.files[path])


class ExploreDeploymentTests(unittest.TestCase):
    def test_only_explore_allowlist(self):
        sftp = FakeSFTP()
        deploy.upload(sftp, "/www/atlas")
        self.assertEqual(sftp.writes, [
            "/www/osservatorio/esplora/" + name for name in deploy.FILES])
        self.assertEqual(sftp.files["/www/osservatorio/index.html"], b"unchanged")
        self.assertEqual(sftp.files["/www/atlas/index.html"], b"unchanged")
        self.assertEqual(sftp.writes[-1], "/www/osservatorio/esplora/index.html")

    def test_reject_symlink_before_upload(self):
        sftp = FakeSFTP()
        sftp.dirs.add("/www/osservatorio/esplora")
        sftp.links.add("/www/osservatorio/esplora/index.html")
        with self.assertRaises(ValueError):
            deploy.upload(sftp, "/www/atlas")
        self.assertFalse(sftp.writes)

    def test_refuse_missing_overview_directory(self):
        sftp = FakeSFTP()
        sftp.dirs.clear()
        with self.assertRaises(FileNotFoundError):
            deploy.upload(sftp, "/www/atlas")
        self.assertFalse(sftp.writes)
