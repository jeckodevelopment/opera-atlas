"""Upload the allowlisted Opera Atlas frontend via OVH SFTP on port 22.

Uses the existing ATLAS_SFTP_* secrets. No server-wide changes or deletes.
"""
from __future__ import annotations

import io
import json
import os
import posixpath
import stat
import tempfile
from pathlib import Path


from scripts.deploy_atlas import FILES, PUBLIC_URL, SANBAPOLIS_ASSET, build, stage_sanbapolis_photo, verify_live


def configuration(env=None):
    env = os.environ if env is None else env
    required = ("ATLAS_SFTP_HOST", "ATLAS_SFTP_USERNAME", "ATLAS_SFTP_REMOTE_DIR")
    missing = [name for name in required if not env.get(name, "").strip()]
    if missing:
        raise ValueError("Missing SFTP configuration: " + ", ".join(missing))
    if not env.get("ATLAS_SFTP_PASSWORD") and not env.get("ATLAS_SFTP_PRIVATE_KEY"):
        raise ValueError("Missing SFTP password or private key")
    host = env["ATLAS_SFTP_HOST"].strip()
    if any(c in host for c in "/:@ "):
        raise ValueError("SFTP host must be a bare hostname")
    target = posixpath.normpath(env["ATLAS_SFTP_REMOTE_DIR"].strip())
    if not target.startswith("/") or target == "/" or not target.endswith("/atlas"):
        raise ValueError("SFTP destination must be an absolute path ending /atlas")
    return {"host": host, "user": env["ATLAS_SFTP_USERNAME"].strip(),
            "password": env.get("ATLAS_SFTP_PASSWORD", ""),
            "key": env.get("ATLAS_SFTP_PRIVATE_KEY", ""),
            "passphrase": env.get("ATLAS_SFTP_KEY_PASSPHRASE") or None,
            "known_hosts": env.get("ATLAS_SFTP_KNOWN_HOSTS", ""),
            "target": target}


def make_client(cfg):
    import paramiko  # installed only by deployment job, not required for stdlib tests
    client = paramiko.SSHClient()
    # Reuse pinned host keys where configured. First-connection fallback
    # follows accept-new behavior; it does not disable SSH encryption.
    for line in cfg["known_hosts"].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        entry = paramiko.hostkeys.HostKeyEntry.from_line(line)
        if entry:
            for hostname in entry.hostnames:
                client.get_host_keys().add(hostname, entry.key.get_name(), entry.key)
    client.set_missing_host_key_policy(paramiko.RejectPolicy() if cfg["known_hosts"].strip() else paramiko.AutoAddPolicy())
    key = None
    if cfg["key"]:
        for kind in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
            try:
                key = kind.from_private_key(io.StringIO(cfg["key"]), password=cfg["passphrase"])
                break
            except (ValueError, paramiko.SSHException):
                pass
        if key is None:
            raise ValueError("Invalid SFTP private key")
    # Use exactly the configured host: the pinned known_hosts entry is host-specific.
    try:
        client.connect(cfg["host"], port=22, username=cfg["user"],
                       password=cfg["password"] or None, pkey=key,
                       look_for_keys=False, allow_agent=False,
                       timeout=30, auth_timeout=30, banner_timeout=30)
    except Exception:
        client.close()
        raise
    return client


def target_path(sftp, configured):
    """Account for OVH exposing the physical home as the SFTP initial directory.

    The configured path takes priority when present. For a chrooted account,
    a path like /homez.2168/account/www/atlas may be visible as /www/atlas.
    Never infer a different web root from the home directory alone.
    """
    home = posixpath.normpath(sftp.normalize("."))
    candidates = [configured]
    if home != "/" and configured.startswith(home + "/"):
        candidates.append(configured[len(home):])
    if home != "/" and not configured.startswith(home + "/"):
        candidates.append(posixpath.join(home, configured.lstrip("/")))
    for path in dict.fromkeys(candidates):
        parent = posixpath.dirname(path)
        try:
            info = sftp.stat(parent)
            if stat.S_ISDIR(info.st_mode):
                return path
        except OSError:
            continue
    raise ValueError("SFTP directory parent not accessible; configured target ends in /atlas; "
                     "verify remote folder relative to the account home (no uploads attempted)")


def publish(env=None, connector=make_client):
    cfg = configuration(env)
    with tempfile.TemporaryDirectory(prefix="atlas-sftp-") as tmp:
        folder = Path(tmp)
        build(folder)
        stage_sanbapolis_photo(folder)
        expected=set(FILES)
        actual={p.name for p in folder.iterdir() if p.is_file()}
        if actual!=expected:
            raise ValueError("Unexpected root release files: "+str(sorted(actual.symmetric_difference(expected))))
        if not (folder / SANBAPOLIS_ASSET).is_file():
            raise ValueError("Missing nested venue image")
        manifest=json.loads((folder/"seo-routes.json").read_text(encoding="utf-8"))
        generated=manifest.get("files",[])
        if not isinstance(generated,list) or len(generated)!=len(set(generated)) or not generated:
            raise ValueError("Invalid generated SEO route manifest")
        for relative in generated:
            if not isinstance(relative,str) or not relative.endswith("/index.html") or not (folder/relative).is_file():
                raise ValueError("Invalid generated SEO file")
        client = connector(cfg)
        try:
            with client.open_sftp() as sftp:
                destination = target_path(sftp, cfg["target"])
                try:
                    info = sftp.lstat(destination)
                except OSError:
                    sftp.mkdir(destination)
                else:
                    if not stat.S_ISDIR(info.st_mode):
                        raise ValueError("SFTP target exists but is not a directory")
                # Only the reviewed asset path is allowed; never follow remote symlinks.
                asset_dir=destination
                for part in SANBAPOLIS_ASSET.split("/")[:-1]:
                    asset_dir=posixpath.join(asset_dir,part)
                    try:
                        info=sftp.lstat(asset_dir)
                    except FileNotFoundError:
                        sftp.mkdir(asset_dir)
                    else:
                        if not stat.S_ISDIR(info.st_mode):
                            raise ValueError("Asset path is not a directory: "+asset_dir)
                # Publish the image before any JS or HTML can reference it.
                sftp.put(str(folder / SANBAPOLIS_ASSET), posixpath.join(destination, SANBAPOLIS_ASSET), confirm=True)
                for name in sorted(FILES):
                    sftp.put(str(folder / name), posixpath.join(destination, name), confirm=True)
                # All paths were checked against the canonical manifest at build.
                # Create only subdirectories owned by canonical Atlas routes.
                made={destination}
                for relative in generated:
                    subdir=posixpath.dirname(posixpath.join(destination,relative))
                    missing=[]
                    candidate=subdir
                    while candidate not in made and candidate!=destination:
                        missing.append(candidate)
                        candidate=posixpath.dirname(candidate)
                    for directory in reversed(missing):
                        try:
                            info=sftp.stat(directory)
                        except OSError:
                            sftp.mkdir(directory)
                        else:
                            if not stat.S_ISDIR(info.st_mode):
                                raise ValueError("Canonical route is not a directory: "+directory)
                        made.add(directory)
                    sftp.put(str(folder/relative),posixpath.join(destination,relative),confirm=True)
                print("Uploaded "+str(len(expected))+" root files, 1 nested venue image and "+str(len(generated))+" canonical HTML pages")
                verify_live(folder)
                print("Verified published Atlas files and deep routes over HTTPS")
        finally:
            client.close()


if __name__ == "__main__":
    publish()
