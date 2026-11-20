"""Migration contract and offline validations for independent opera.plus publisher."""
import tempfile
import unittest
import shutil
import subprocess
from pathlib import Path

from scripts.deploy_atlas import ROOT, SOURCE, FILES, PUBLIC_URL, build, settings

class AtlasMigrationTests(unittest.TestCase):
    def test_all_static_pages_point_to_new_base(self):
        for name in ("index.html","detail.html","directory.html","privacy.html","credits.html"):
            html=(SOURCE/name).read_text(encoding="utf-8")
            self.assertIn('<base href="/atlas/">',html,name)
            self.assertNotIn("/dev/opera-atlas",html,name)
        rewrite=(SOURCE/".htaccess").read_text(encoding="utf-8")
        self.assertIn("RewriteBase /atlas/",rewrite)
        self.assertNotIn("/dev/opera-atlas",rewrite)
        self.assertEqual(PUBLIC_URL,"https://opera.plus/atlas/")

    def test_static_js_routes_use_shared_base_and_no_legacy_origin(self):
        for path in SOURCE.iterdir():
            if path.suffix in (".js",".html",".css") or path.name==".htaccess":
                content=path.read_text(encoding="utf-8")
                self.assertNotIn("/dev/opera-atlas",content,path.name)
                self.assertNotIn("jeckodevelopment.com/dev/opera-atlas",content,path.name)
        client=(SOURCE/"catalog-client.js").read_text(encoding="utf-8")
        self.assertIn("new URL(document.baseURI).pathname",client)
        self.assertIn("raw.githubusercontent.com/jeckodevelopment/opera-atlas",client)
        detail=(SOURCE/"detail.js").read_text(encoding="utf-8")
        self.assertIn("new URL(document.baseURI).pathname",detail)

    def test_release_is_allowlisted_and_cache_busted(self):
        self.assertNotIn(".env",FILES)
        self.assertNotIn("config.json",FILES)
        with tempfile.TemporaryDirectory() as path:
            folder=Path(path)
            build(folder)
            self.assertEqual({p.name for p in folder.iterdir()},set(FILES))
            html=(folder/"index.html").read_text(encoding="utf-8")
            self.assertIn("styles.css?v=",html)
            self.assertIn("app.js?v=",html)
            self.assertIn('<base href="/atlas/">',html)
            self.assertNotIn("/dev/opera-atlas",html)
            self.assertIn("RewriteBase /atlas/",(folder/".htaccess").read_text())

    def test_settings_cannot_deploy_to_account_root_or_wrong_host(self):
        base={"ATLAS_SFTP_HOST":"sftp.example",
              "ATLAS_SFTP_USERNAME":"atlas",
              "ATLAS_SFTP_KNOWN_HOSTS":"sftp.example ssh-ed25519 AAAATEST",
              "ATLAS_SFTP_PASSWORD":"test"}
        for target in ("/","/atlas","/var/www","/var/www/other","relative/atlas"):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    settings({**base,"ATLAS_SFTP_REMOTE_DIR":target})
        config=settings({**base,"ATLAS_SFTP_REMOTE_DIR":"/var/www/atlas"})
        self.assertEqual(config["target"],"/var/www/atlas")
        with self.assertRaises(ValueError):
            settings({**base,"ATLAS_SFTP_REMOTE_DIR":"/var/www/atlas",
                      "ATLAS_SFTP_PRIVATE_KEY":"also supplied"})

    @unittest.skipUnless(shutil.which("node"),"Node.js unavailable")
    def test_actual_catalog_url_builder(self):
        test=subprocess.run(["node",str(ROOT/"tests/atlas_routes_smoke.cjs")],
                            cwd=ROOT,text=True,capture_output=True)
        self.assertEqual(test.returncode,0,test.stdout+"\n"+test.stderr)

if __name__=="__main__":
    unittest.main()
