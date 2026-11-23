"""Independent Opera Atlas plain FTP release with HTTPS verification and rollback.

Only the application-owned /atlas directory can be changed; the main site is untouched.
No dependency on jeckodevsite. Plain FTP sends credentials and files unencrypted.
"""
from __future__ import annotations
import hashlib
import io
from ftplib import FTP, error_perm
import json
import os
import posixpath
import re
import tempfile
import time
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site"
PUBLIC_URL = "https://opera.plus/atlas/"
FILES = frozenset((
    ".htaccess", "index.html", "detail.html", "directory.html", "in-scena.html",
    "privacy.html", "credits.html", "app.js", "detail.js",
    "directory.js", "in-scena.js", "in-scena.css", "festival-client.js", "image-client.js",
    "catalog-client.js", "styles.css", "atlas-logo.svg",
    "opera-stage.svg", "cover-jenufa.svg", "cover-nixon-in-china.svg", "performances.json", "work-synopses.json",
    "work-history.json", "theatre-profiles.json", "og-atlas.png", "sitemap.xml", "seo-routes.json"
))
# Keep this allowlist explicit; no dotfiles except routing .htaccess,
# no credentials, test fixtures, scripts or automatic catalog data.
FINGERPRINT = frozenset(("styles.css", "app.js", "detail.js", "directory.js",
                         "catalog-client.js", "festival-client.js", "image-client.js", "in-scena.js", "in-scena.css"))
CANONICAL = ("opere/la-traviata/", "torino/teatro-regio/",
             "torino/teatro-regio/la-traviata/",
             "produzioni/oa-g-lombardia-italiana-2026/")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    generated = {"og-atlas.png", "sitemap.xml", "seo-routes.json"}
    for filename in sorted(FILES - generated):
        src = SOURCE / filename
        if not src.is_file() or src.is_symlink():
            raise ValueError("Missing or unsafe Atlas source: " + filename)
        data = src.read_bytes()
        if len(data) > 3_000_000:
            raise ValueError("Oversized frontend file: " + filename)
        (destination / filename).write_bytes(data)
    from scripts.atlas_seo import build as build_seo
    build_seo(destination, ROOT / "public" / "catalog" / "v2")
    snapshot = json.loads((destination / "performances.json").read_text(encoding="utf-8"))
    if snapshot.get("schema_version") != 1 or not isinstance(snapshot.get("performances"), list):
        raise ValueError("Invalid static snapshot")
    for filename in ("index.html", "detail.html", "directory.html", "in-scena.html", "privacy.html", "credits.html"):
        html = (destination / filename).read_text(encoding="utf-8")
        if '<base href="/atlas/">' not in html:
            raise ValueError("Incorrect public base in " + filename)
        for asset in sorted(FINGERPRINT):
            pattern = r'((?:href|src)="\./)' + re.escape(asset) + r'(?:\?[^"]*)?(")'
            if re.search(pattern, html):
                html = re.sub(pattern, lambda match:
                    match.group(1) + asset + "?v=" + sha((destination / asset).read_bytes())[:12] + match.group(2), html)
        (destination / filename).write_text(html, encoding="utf-8")
    from scripts.prerender_atlas import generate as generate_entity_pages
    generate_entity_pages(destination, ROOT / "public" / "catalog" / "v2")
    if "RewriteBase /atlas/" not in (destination / ".htaccess").read_text(encoding="utf-8"):
        raise ValueError("Incorrect rewrite base")
    for filename in ("catalog-client.js", "detail.js"):
        if "/dev/opera-atlas" in (destination / filename).read_text(encoding="utf-8"):
            raise ValueError("Old route embedded in " + filename)


def settings(env: dict | None = None) -> dict:
    env = os.environ if env is None else env
    required = ("ATLAS_FTP_HOST", "ATLAS_FTP_USERNAME",
                "ATLAS_FTP_REMOTE_DIR", "ATLAS_FTP_PASSWORD")
    missing = [key for key in required if not env.get(key, "").strip()]
    if missing:
        raise ValueError("Missing FTP deployment configuration: " + ", ".join(missing))
    host = env["ATLAS_FTP_HOST"].strip()
    if "://" in host or "/" in host or "@" in host or not host:
        raise ValueError("ATLAS_FTP_HOST must be a bare host name")
    target = posixpath.normpath(env["ATLAS_FTP_REMOTE_DIR"].strip())
    if not target.startswith("/") or target == "/" or not target.endswith("/atlas"):
        raise ValueError("ATLAS_FTP_REMOTE_DIR must be an absolute folder ending in /atlas")
    # FTP servers often chroot users into their account's webroot; /atlas is valid.
    port = int(env.get("ATLAS_FTP_PORT") or "21")
    if not 1 <= port <= 65535:
        raise ValueError("Invalid ATLAS_FTP_PORT")
    return {"host": host, "username": env["ATLAS_FTP_USERNAME"].strip(),
            "password": env["ATLAS_FTP_PASSWORD"], "port": port, "target": target}


def connect(config):
    """Connect with plain FTP on port 21, as required by the hosting service.

    Warning: FTP sends the username, password, and transferred files unencrypted.
    """
    ftp = FTP(timeout=30, encoding="utf-8")
    try:
        ftp.connect(config["host"], config["port"], timeout=30)
        ftp.login(config["username"], config["password"])
        ftp.set_pasv(True)
        return ftp
    except BaseException:
        ftp.close()
        raise


def is_dir(ftp, directory: str) -> bool:
    previous = ftp.pwd()
    try:
        ftp.cwd(directory)
        return True
    except error_perm as error:
        if not str(error).startswith(("550", "553")):
            raise
        return False
    finally:
        ftp.cwd(previous)


def delete_owned_files(ftp, directory: str) -> None:
    """Remove only allowlisted top-level application files in a known snapshot."""
    if not is_dir(ftp, directory):
        return
    # Do not remove arbitrary user uploads or subdirectories inside /atlas.
    for name in sorted(FILES):
        try:
            ftp.delete(posixpath.join(directory, name))
        except error_perm as error:
            if not str(error).startswith(("550", "553")):
                raise
    # If unknown files remain, RMD fails rather than deleting them.
    ftp.rmd(directory)


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
            for route in CANONICAL:
                req=Request(PUBLIC_URL+route+"?release="+nonce,
                            headers={"Cache-Control":"no-cache","User-Agent":"OperaAtlasPublisher/1.0"})
                with urlopen(req,timeout=20) as response:
                    expected_page=folder/route/"index.html"
                    if not expected_page.is_file() or response.status!=200 or sha(response.read(3_000_001))!=sha(expected_page.read_bytes()):
                        raise RuntimeError("Atlas static SEO page failure: "+route)
            req=Request(PUBLIC_URL+"in-scena?release="+nonce,headers={"Cache-Control":"no-cache","User-Agent":"OperaAtlasPublisher/1.0"})
            with urlopen(req,timeout=20) as response:
                if response.status!=200 or sha(response.read(3_000_001))!=sha((folder/"in-scena.html").read_bytes()):
                    raise RuntimeError("Atlas In scena canonical slashless route failure")
            return
        except Exception:
            if attempt==2:raise
            time.sleep(3)


def publish(ftp, folder: Path, target: str, verifier=verify_live) -> None:
    parent = posixpath.dirname(target)
    if not is_dir(ftp, parent):
        raise ValueError("FTP parent directory unavailable: verify document root")
    token = uuid.uuid4().hex[:16]
    stage = posixpath.join(parent, ".atlas-stage-" + token)
    backup = posixpath.join(parent, ".atlas-backup-" + token)
    failed = posixpath.join(parent, ".atlas-failed-" + token)
    deployed = False
    backed_up = False
    ftp.mkd(stage)
    try:
        for name in sorted(FILES):
            with (folder / name).open("rb") as source:
                ftp.storbinary("STOR " + posixpath.join(stage, name), source)
        for name in sorted(FILES):
            chunks = []
            ftp.retrbinary("RETR " + posixpath.join(stage, name), chunks.append)
            if sha(b"".join(chunks)) != sha((folder / name).read_bytes()):
                raise RuntimeError("FTP uploaded file digest mismatch: " + name)
        if is_dir(ftp, target):
            # Never switch an existing directory that includes unknown files.
            # The first migration requires a clean /atlas directory.
            unexpected = []
            for entry in ftp.nlst(target):
                basename = posixpath.basename(entry.rstrip("/"))
                if basename and basename not in FILES:
                    unexpected.append(basename)
            if unexpected:
                raise ValueError("Atlas target contains unmanaged files; refusing deploy: " +
                                 ", ".join(sorted(unexpected)))
            ftp.rename(target, backup)
            backed_up = True
        try:
            ftp.rename(stage, target)
            deployed = True
            verifier(folder)
        except BaseException:
            if deployed:
                ftp.rename(target, failed)
            if backed_up:
                ftp.rename(backup, target)
                backed_up = False
            raise
        if backed_up:
            delete_owned_files(ftp, backup)
            backed_up = False
    finally:
        # Never mask a deployment error with an ancillary cleanup failure.
        # Never clean directories not owned by this invocation.
        if is_dir(ftp, stage):
            delete_owned_files(ftp, stage)
        if is_dir(ftp, failed):
            delete_owned_files(ftp, failed)


def main():
    config=settings()
    with tempfile.TemporaryDirectory(prefix="atlas-release-") as temp:
        folder=Path(temp)
        build(folder)  # fail before connecting for missing assets or invalid URLs
        ftp=connect(config)
        try:
            publish(ftp,folder,config["target"])
        finally:
            try:
                ftp.quit()
            except Exception:
                ftp.close()
    print("Published and verified "+PUBLIC_URL)


if __name__=="__main__":
    main()
