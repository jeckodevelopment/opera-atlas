"""Independent, allowlisted Opera Atlas SFTP release with HTTPS validation and rollback.

SFTP remote directory points to the atlas *application* folder itself, never
the hosting account's web root. No dependency on jeckodevsite.
"""
from __future__ import annotations
import hashlib
import io
import json
import os
import posixpath
import re
import stat
import tempfile
import time
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site"
PUBLIC_URL = "https://opera.plus/atlas/"
FILES = frozenset((
    ".htaccess", "index.html", "detail.html", "directory.html",
    "privacy.html", "credits.html", "app.js", "detail.js",
    "directory.js", "festival-client.js", "image-client.js",
    "catalog-client.js", "styles.css", "atlas-logo.svg",
    "opera-stage.svg", "performances.json", "work-synopses.json",
    "work-history.json", "theatre-profiles.json"
))
# Keep this allowlist explicit; no dotfiles except routing .htaccess,
# no credentials, test fixtures, scripts or automatic catalog data.
FINGERPRINT = frozenset(("styles.css", "app.js", "detail.js", "directory.js",
                         "catalog-client.js", "festival-client.js", "image-client.js"))
CANONICAL = ("opere/la-traviata/", "torino/teatro-regio/",
             "torino/teatro-regio/la-traviata/",
             "produzioni/oa-g-lombardia-italiana-2026/")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for filename in sorted(FILES):
        src = SOURCE / filename
        if not src.is_file() or src.is_symlink():
            raise ValueError("Missing or unsafe Atlas source: " + filename)
        data = src.read_bytes()
        if len(data) > 3_000_000:
            raise ValueError("Oversized frontend file: " + filename)
        (destination / filename).write_bytes(data)
    snapshot = json.loads((destination / "performances.json").read_text(encoding="utf-8"))
    if snapshot.get("schema_version") != 1 or not isinstance(snapshot.get("performances"), list):
        raise ValueError("Invalid static snapshot")
    for filename in ("index.html", "detail.html", "directory.html", "privacy.html", "credits.html"):
        html = (destination / filename).read_text(encoding="utf-8")
        if '<base href="/atlas/">' not in html:
            raise ValueError("Incorrect public base in " + filename)
        for asset in sorted(FINGERPRINT):
            pattern = r'((?:href|src)="\./)' + re.escape(asset) + r'(?:\?[^"]*)?(")'
            if re.search(pattern, html):
                html = re.sub(pattern, lambda match:
                    match.group(1) + asset + "?v=" + sha((destination / asset).read_bytes())[:12] + match.group(2), html)
        (destination / filename).write_text(html, encoding="utf-8")
    if "RewriteBase /atlas/" not in (destination / ".htaccess").read_text(encoding="utf-8"):
        raise ValueError("Incorrect rewrite base")
    for filename in ("catalog-client.js", "detail.js"):
        if "/dev/opera-atlas" in (destination / filename).read_text(encoding="utf-8"):
            raise ValueError("Old route embedded in " + filename)


def settings(env: dict | None = None) -> dict:
    env = os.environ if env is None else env
    required = ("ATLAS_SFTP_HOST", "ATLAS_SFTP_USERNAME",
                "ATLAS_SFTP_REMOTE_DIR", "ATLAS_SFTP_KNOWN_HOSTS")
    missing = [key for key in required if not env.get(key, "").strip()]
    if missing:
        raise ValueError("Missing deployment configuration: " + ", ".join(missing))
    password = env.get("ATLAS_SFTP_PASSWORD", "")
    private = env.get("ATLAS_SFTP_PRIVATE_KEY", "")
    if bool(password) == bool(private):
        raise ValueError("Exactly one of ATLAS_SFTP_PASSWORD or ATLAS_SFTP_PRIVATE_KEY is required")
    target = posixpath.normpath(env["ATLAS_SFTP_REMOTE_DIR"])
    if not target.startswith("/") or target in ("/", "/atlas") or not target.endswith("/atlas"):
        raise ValueError("ATLAS_SFTP_REMOTE_DIR must be the absolute account path ending in /atlas, not the document root")
    port = int(env.get("ATLAS_SFTP_PORT", "22"))
    if not 1 <= port <= 65535:raise ValueError("Invalid ATLAS_SFTP_PORT")
    return {"host":env["ATLAS_SFTP_HOST"],"username":env["ATLAS_SFTP_USERNAME"],
            "known_hosts":env["ATLAS_SFTP_KNOWN_HOSTS"],"password":password,
            "private_key":private,"passphrase":env.get("ATLAS_SFTP_KEY_PASSPHRASE",""),
            "port":port,"target":target}


def connect(config):
    import paramiko
    client = paramiko.SSHClient()
    entries = 0
    for line in config["known_hosts"].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):continue
        entry = paramiko.hostkeys.HostKeyEntry.from_line(line)
        if not entry:raise ValueError("Invalid pinned host key")
        for host in entry.hostnames:
            client.get_host_keys().add(host,entry.key.get_name(),entry.key)
            entries += 1
    if not entries:raise ValueError("No pinned SFTP host key")
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    key = None
    if config["private_key"]:
        for key_cls in (paramiko.Ed25519Key,paramiko.RSAKey,paramiko.ECDSAKey):
            try:
                key = key_cls.from_private_key(io.StringIO(config["private_key"]),
                                               password=config["passphrase"] or None)
                break
            except (ValueError,paramiko.SSHException):
                continue
        if key is None:raise ValueError("Unsupported SFTP private key")
    client.connect(config["host"],port=config["port"],
                   username=config["username"],password=config["password"] or None,
                   pkey=key,allow_agent=False,look_for_keys=False,timeout=25,
                   banner_timeout=25,auth_timeout=25)
    return client


def exists(sftp, filename: str) -> bool:
    try:sftp.lstat(filename);return True
    except FileNotFoundError:return False


def clean(sftp, directory: str) -> None:
    for entry in sftp.listdir_attr(directory):
        path = posixpath.join(directory,entry.filename)
        if stat.S_ISDIR(entry.st_mode):clean(sftp,path)
        else:sftp.remove(path)
    sftp.rmdir(directory)


def verify_live(folder: Path) -> None:
    # Validate actual public bytes instead of mistaking generic 404 HTML for success.
    for attempt in range(3):
        try:
            nonce=uuid.uuid4().hex
            for file in sorted(FILES- {".htaccess"}):
                req=Request(PUBLIC_URL+file+"?release="+nonce,
                            headers={"Cache-Control":"no-cache","User-Agent":"OperaAtlasPublisher/1.0"})
                with urlopen(req,timeout=20) as response:
                    if response.status!=200 or sha(response.read(3_000_001))!=sha((folder/file).read_bytes()):
                        raise RuntimeError("Atlas public asset mismatch: "+file)
            expected=sha((folder/"detail.html").read_bytes())
            for route in CANONICAL:
                req=Request(PUBLIC_URL+route+"?release="+nonce,
                            headers={"Cache-Control":"no-cache","User-Agent":"OperaAtlasPublisher/1.0"})
                with urlopen(req,timeout=20) as response:
                    if response.status!=200 or sha(response.read(3_000_001))!=expected:
                        raise RuntimeError("Atlas deep-route rewrite failure: "+route)
            return
        except Exception:
            if attempt==2:raise
            time.sleep(3)


def publish(sftp,folder:Path,target:str,verifier=verify_live) -> None:
    parent=posixpath.dirname(target)
    if not stat.S_ISDIR(sftp.stat(parent).st_mode):
        raise ValueError("Atlas parent directory unavailable")
    # Never touch files outside the configured /atlas folder or own stage/backup.
    token=uuid.uuid4().hex[:16]
    stage=posixpath.join(parent,".atlas-stage-"+token)
    backup=posixpath.join(parent,".atlas-backup-"+token)
    failed=posixpath.join(parent,".atlas-failed-"+token)
    deployed=False
    backed_up=False
    sftp.mkdir(stage)
    try:
        for file in sorted(FILES):
            sftp.put(str(folder/file),posixpath.join(stage,file))
        for file in sorted(FILES):
            with sftp.open(posixpath.join(stage,file),"rb") as remote:
                if sha(remote.read())!=sha((folder/file).read_bytes()):
                    raise RuntimeError("SFTP upload checksum mismatch: "+file)
        if exists(sftp,target):
            if not stat.S_ISDIR(sftp.lstat(target).st_mode):
                raise ValueError("Target is not a directory")
            sftp.rename(target,backup)
            backed_up=True
        try:
            sftp.rename(stage,target)
            deployed=True
            verifier(folder)
        except Exception:
            if deployed:
                sftp.rename(target,failed)
            if backed_up:
                sftp.rename(backup,target)
                backed_up=False
            raise
        if backed_up:
            clean(sftp,backup)
            backed_up=False
    finally:
        # On rollback, retain only a failed snapshot if it could not be cleaned
        # without touching another path. The prior valid website is restored.
        if exists(sftp,stage):clean(sftp,stage)
        if exists(sftp,failed):clean(sftp,failed)


def main():
    config=settings()
    with tempfile.TemporaryDirectory(prefix="atlas-release-") as temp:
        folder=Path(temp)
        build(folder)  # fail before connecting for missing assets or invalid URLs
        client=connect(config)
        try:
            with client.open_sftp() as sftp:
                publish(sftp,folder,config["target"])
        finally:
            client.close()
    print("Published and verified "+PUBLIC_URL)


if __name__=="__main__":
    main()
