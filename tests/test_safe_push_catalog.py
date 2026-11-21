"""Real local Git races: no force push, safe rebase, and stale-data deferral."""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import unittest
import os
from unittest.mock import patch
from scripts import safe_push_catalog

from scripts.safe_push_catalog import safe_push, source_affecting

def execute(repo:Path,*args:str)->str:
    command=subprocess.run(["git",*args],cwd=repo,text=True,
                           capture_output=True,check=False)
    if command.returncode:
        raise AssertionError(command.stderr)
    return command.stdout.strip()

class SafePushTests(unittest.TestCase):
    def setup_repos(self,tmp):
        root=Path(tmp)
        remote=root/"remote.git"
        remote.mkdir()
        execute(root,"init","--bare","-b","main",str(remote))
        base=root/"base"
        base.mkdir()
        execute(base,"init","-b","main")
        execute(base,"config","user.email","atlas-tests@example.invalid")
        execute(base,"config","user.name","Atlas Test")
        execute(base,"remote","add","origin",str(remote))
        for filename,value in {
            "data/catalog.json":"{}\n",
            "scripts/adapter.py":"BASE=True\n",
            "docs/notes.md":"Original notes\n"}.items():
            target=base/filename
            target.parent.mkdir(exist_ok=True)
            target.write_text(value)
        execute(base,"add",".")
        execute(base,"commit","-m","initial")
        execute(base,"push","-u","origin","main")
        pub=root/"publisher"
        writer=root/"writer"
        execute(root,"clone","--branch","main",str(remote),str(pub))
        execute(root,"clone","--branch","main",str(remote),str(writer))
        for repo in (pub,writer):
            execute(repo,"config","user.email","atlas-tests@example.invalid")
            execute(repo,"config","user.name","Atlas Test")
        (pub/"data/catalog.json").write_text('{"new":"recite"}\n')
        execute(pub,"add",".")
        execute(pub,"commit","-m","data catalog refresh")
        return pub,writer,remote

    def test_only_unrelated_docs_changed_upstream_rebases_then_publishes(self):
        with TemporaryDirectory() as tmp:
            pub,writer,remote=self.setup_repos(tmp)
            (writer/"docs/notes.md").write_text("New documentation\n")
            execute(writer,"add",".")
            execute(writer,"commit","-m","documentation update")
            execute(writer,"push","origin","main")
            validations=[]
            result=safe_push(pub,verify=lambda _:validations.append(True))
            self.assertEqual(result,"published")
            self.assertEqual(validations,[True])
            clone=Path(tmp)/"proof"
            execute(Path(tmp),"clone","-b","main",str(remote),str(clone))
            self.assertEqual((clone/"data/catalog.json").read_text(),
                             '{"new":"recite"}\n')
            self.assertEqual((clone/"docs/notes.md").read_text(),
                             "New documentation\n")

    def test_new_parser_in_upstream_defers_stale_catalog_commit(self):
        with TemporaryDirectory() as tmp:
            pub,writer,remote=self.setup_repos(tmp)
            (writer/"scripts/adapter.py").write_text("NEW_ADAPTER=True\n")
            execute(writer,"add",".")
            execute(writer,"commit","-m","new parser")
            execute(writer,"push","origin","main")
            result=safe_push(pub,verify=lambda _:self.fail("must not validate stale data"))
            self.assertEqual(result,"deferred")
            clone=Path(tmp)/"proof"
            execute(Path(tmp),"clone","-b","main",str(remote),str(clone))
            self.assertEqual((clone/"data/catalog.json").read_text(),"{}\n")
            self.assertEqual((clone/"scripts/adapter.py").read_text(),"NEW_ADAPTER=True\n")

    def test_multiple_unpublished_catalog_commits_and_new_main_defer_cleanly(self):
        with TemporaryDirectory() as tmp:
            pub,writer,remote=self.setup_repos(tmp)
            # The refresh generated more than one local commit while another
            # change reached main; HEAD^ is no longer on origin/main.
            (pub/"docs/notes.md").write_text("Local note\n")
            execute(pub,"add",".")
            execute(pub,"commit","-m","local post-checkpoint note")
            (writer/"scripts/adapter.py").write_text("NEW_ADAPTER=True\n")
            execute(writer,"add",".")
            execute(writer,"commit","-m","concurrent adapter")
            execute(writer,"push","origin","main")
            result=safe_push(pub,verify=lambda _:self.fail(
                "must not rebase or publish stale catalog"))
            self.assertEqual(result,"deferred")
            clone=Path(tmp)/"proof"
            execute(Path(tmp),"clone","-b","main",str(remote),str(clone))
            self.assertEqual((clone/"data/catalog.json").read_text(),"{}\n")
            self.assertEqual((clone/"scripts/adapter.py").read_text(),
                             "NEW_ADAPTER=True\n")

    def test_deferred_push_emits_workflow_retry_output(self):
        with TemporaryDirectory() as tmp:
            output=Path(tmp)/"github_output"
            for result,expected in (("deferred","deferred=true\n"),
                                    ("published","deferred=false\n")):
                output.write_text("")
                with patch.dict(os.environ,{"GITHUB_OUTPUT":str(output)}):
                    with patch.object(safe_push_catalog,"safe_push",return_value=result):
                        safe_push_catalog.main()
                self.assertEqual(output.read_text(),expected)

    def test_sensitive_prefixes_cover_registry_catalog_and_code(self):
        self.assertTrue(source_affecting(["data/identity-registry.json"]))
        self.assertTrue(source_affecting(["public/catalog/v2/manifest.json"]))
        self.assertTrue(source_affecting(["opera_atlas/national_detail_parser.py"]))
        self.assertFalse(source_affecting(["docs/SOURCE_ONBOARDING.md"]))
        self.assertFalse(source_affecting(["site/logo.svg"]))
if __name__=="__main__":
    unittest.main()
