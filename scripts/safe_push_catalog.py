"""Safely publish a validated catalog commit despite concurrent main updates.

Never force-push or replay stale catalog changes over newer source/code.
A harmless docs-only concurrent commit may be rebased after validation.
A substantive concurrent update is deferred to its own/new scheduled refresh.
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

SENSITIVE_PREFIXES=(
    "data/","public/catalog/","scripts/","opera_atlas/","tests/",
    ".github/","site/work-synopses.json","site/work-history.json",
    "site/performances.json",
)

def source_affecting(paths:list[str])->bool:
    return any(path.startswith(SENSITIVE_PREFIXES) for path in paths)

def git(repo:Path,*args:str,check:bool=True)->subprocess.CompletedProcess:
    call=subprocess.run(["git",*args],cwd=repo,encoding="utf-8",
                        text=True,capture_output=True,check=False)
    if check and call.returncode:
        raise RuntimeError(f"git {args[0]} failed: {call.stderr.strip()}")
    return call

def safe_push(repo:Path,*,verify=None,max_attempts:int=3)->str:
    """Return 'published' or 'deferred'; raise on nonrecoverable errors.

    A deferred push is *not* a publication claim. The newer main push and
    scheduled daily job independently rebuild the canonical JSON.
    """
    if max_attempts<1:raise ValueError("invalid retry count")
    repo=Path(repo)
    for attempt in range(max_attempts):
        push=git(repo,"push","origin","HEAD:main",check=False)
        if push.returncode==0:return "published"
        git(repo,"fetch","origin","main")
        head=git(repo,"rev-parse","HEAD").stdout.strip()
        upstream=git(repo,"rev-parse","origin/main").stdout.strip()
        # A network error after a successful push must not create a second
        # data commit or be reported as a conflict.
        if git(repo,"merge-base","--is-ancestor",head,upstream,
               check=False).returncode==0:
            return "published"
        base=git(repo,"rev-parse","HEAD^").stdout.strip()
        if git(repo,"merge-base","--is-ancestor",base,upstream,
               check=False).returncode!=0:
            # A prior checkpoint or another writer can create multiple local
            # commits while main advances. This is a stale output, *not* an
            # irrecoverable git failure. Never replay the outdated catalog:
            # allow the workflow's retry dispatch to build on current main.
            print("::warning::Catalog push deferred: publication history "
                  "diverged after concurrent changes; refresh latest main.")
            return "deferred"
        changed=git(repo,"diff","--name-only",base,upstream).stdout.splitlines()
        if source_affecting(changed):
            print("::warning::Catalog push deferred: upstream source or canonical "
                  "data changed; a newer or scheduled refresh will rebuild.")
            return "deferred"
        # Safe: only docs or unrelated site assets changed upstream. Rebase
        # the generated commit and validate the resulting tree before retry.
        git(repo,"rebase","origin/main")
        if verify is not None:verify(repo)
    raise RuntimeError("catalog push failed after bounded retries")

def validate_after_rebase(repo:Path):
    tasks=[
        [sys.executable,"-m","unittest","discover","-s","tests","-v"],
        [sys.executable,"-m","scripts.build_verified_catalog","--check"],
        [sys.executable,"-m","scripts.publish_catalog_v2","--check"],
        [sys.executable,"-m","scripts.publish_work_editorial","--check"],
    ]
    for task in tasks:
        completed=subprocess.run(task,cwd=repo,check=False)
        if completed.returncode:
            raise RuntimeError("rebased catalog failed canonical validation")

def main():
    result=safe_push(Path.cwd(),verify=validate_after_rebase)
    print(f"Catalog push result: {result}")
    output=os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output,"a",encoding="utf-8") as stream:
            stream.write(f"deferred={str(result == 'deferred').lower()}\n")
if __name__=="__main__":
    main()
