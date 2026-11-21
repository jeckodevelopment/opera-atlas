"""Simple plain FTP uploader for the Atlas static site on OVH.

Uses the existing ATLAS_SFTP_* GitHub secrets through the ATLAS_FTP_* env mapping.
FTP transmits credentials and files without encryption. No deletions on the server.
"""
from __future__ import annotations

import json
import os
import posixpath
import re
import subprocess
import tempfile
from pathlib import Path

from scripts.deploy_atlas import build, FILES, PUBLIC_URL


def quote_lftp(value: str) -> str:
    # lftp accepts double-quoted command arguments and backslash escaping.
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r') + '"'


def configuration(env=None):
    env = os.environ if env is None else env
    names = ('ATLAS_FTP_HOST', 'ATLAS_FTP_USERNAME', 'ATLAS_FTP_PASSWORD', 'ATLAS_FTP_REMOTE_DIR')
    missing = [key for key in names if not env.get(key)]
    if missing:
        raise ValueError('Missing FTP settings: ' + ', '.join(missing))
    host = env['ATLAS_FTP_HOST'].strip()
    if not re.fullmatch(r'[A-Za-z0-9.-]+', host):
        raise ValueError('Invalid FTP hostname')
    target = posixpath.normpath(env['ATLAS_FTP_REMOTE_DIR'].strip())
    if not target.startswith('/') or not target.endswith('/atlas'):
        raise ValueError('FTP target must be an absolute path ending in /atlas')
    if target == '/':
        raise ValueError('Refusing to publish to FTP root')
    return host, env['ATLAS_FTP_USERNAME'], env['ATLAS_FTP_PASSWORD'], target


def publish(env=None, runner=subprocess.run):
    host, username, password, target = configuration(env)
    with tempfile.TemporaryDirectory(prefix='atlas-ftp-') as temp:
        folder = Path(temp) / 'site'
        build(folder)  # Build and validate before opening a connection.
        if {p.name for p in folder.iterdir()} != set(FILES):
            raise ValueError('Unexpected files in release folder')
        # Never enable TLS; use one standard passive-mode FTP session.
        commands = '\n'.join((
            'set ftp:ssl-allow no',
            'set ftp:passive-mode yes',
            'set net:max-retries 1',
            'set net:timeout 30',
            'set cmd:fail-exit yes',
            'open -u ' + quote_lftp(username) + ',' + quote_lftp(password) + ' ' + quote_lftp('ftp://' + host + ':21'),
            'mirror --reverse --all --overwrite --no-perms ' + quote_lftp(str(folder)) + ' ' + quote_lftp(target),
            'bye',
            '',
        ))
        completed = runner(['lftp', '-f', '/dev/stdin'], input=commands, text=True, capture_output=True)
        if completed.returncode:
            # Do not dump client output: some clients echo usernames or commands.
            raise RuntimeError('FTP upload failed (lftp exit code ' + str(completed.returncode) + '). Check FTP login and target in OVH.')
        print('Uploaded ' + str(len(FILES)) + ' Atlas files via plain FTP to ' + PUBLIC_URL)


if __name__ == '__main__':
    publish()
