"""Migration contract and offline validations for independent opera.plus publisher."""
import tempfile
import unittest
import shutil
import subprocess
from pathlib import Path

from scripts.deploy_atlas import ROOT, SOURCE, FILES, PUBLIC_URL, build, settings

class AtlasMigrationTests(unittest.TestCase):
    def test_deploy_regenerates_canonical_feeds_before_checking_them(self):
        workflow=(ROOT/".github/workflows/deploy-atlas.yml").read_text(encoding="utf-8")
        build_step=workflow.index("- name: Build current canonical feed for preflight")
        check_step=workflow.index("- name: Verify canonical routes and app")
        sftp_step=workflow.index("- name: Upload Atlas static files via SFTP")
        self.assertLess(build_step,check_step)
        self.assertLess(check_step,sftp_step)
        for cmd in ("python -m scripts.build_verified_catalog",
                    "python -m scripts.publish_catalog_v2",
                    "python -m scripts.publish_work_editorial"):
            self.assertIn(cmd,workflow[build_step:check_step])
            self.assertIn(cmd+" --check",workflow[check_step:sftp_step])
        self.assertNotIn("git push",workflow)

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
            self.assertEqual({p.name for p in folder.iterdir() if p.is_file()},set(FILES))
            self.assertTrue((folder/'opere/la-traviata/index.html').is_file())
            html=(folder/"index.html").read_text(encoding="utf-8")
            self.assertIn("styles.css?v=",html)
            self.assertIn("app.js?v=",html)
            self.assertIn('<base href="/atlas/">',html)
            self.assertNotIn("/dev/opera-atlas",html)
            self.assertIn("RewriteBase /atlas/",(folder/".htaccess").read_text())

    def test_settings_require_ftp_credentials_and_isolated_atlas_path(self):
        base={"ATLAS_FTP_HOST":"ftp.example.org",
              "ATLAS_FTP_USERNAME":"atlas",
              "ATLAS_FTP_PASSWORD":"test"}
        for target in ("/","/var/www","/var/www/other","relative/atlas"):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    settings({**base,"ATLAS_FTP_REMOTE_DIR":target})
        config=settings({**base,"ATLAS_FTP_REMOTE_DIR":"/atlas"})
        self.assertEqual(config["target"],"/atlas")
        self.assertEqual(config["port"],21)
        config=settings({**base,"ATLAS_FTP_REMOTE_DIR":"/var/www/atlas"})
        self.assertEqual(config["target"],"/var/www/atlas")
        with self.assertRaises(ValueError):
            settings({**base,"ATLAS_FTP_HOST":"ftp://ftp.example.org",
                      "ATLAS_FTP_REMOTE_DIR":"/atlas"})
        with self.assertRaises(ValueError):
            settings({k:v for k,v in {**base,"ATLAS_FTP_REMOTE_DIR":"/atlas"}.items()
                      if k!="ATLAS_FTP_PASSWORD"})

    def test_ovh_sftp_uses_existing_secret_names_and_port22(self):
        workflow=(ROOT/".github/workflows/deploy-atlas.yml").read_text(encoding="utf-8")
        for suffix in ("HOST", "USERNAME", "PASSWORD", "REMOTE_DIR",
                       "PRIVATE_KEY", "KNOWN_HOSTS", "KEY_PASSPHRASE"):
            self.assertIn("secrets.ATLAS_SFTP_" + suffix,workflow)
        self.assertIn("scripts.deploy_atlas_sftp",workflow)
        self.assertIn("paramiko",workflow)
        self.assertNotIn("scripts.deploy_atlas_simple_ftp",workflow.split("        run: timeout")[-1])
        script=(ROOT/"scripts/deploy_atlas_sftp.py").read_text(encoding="utf-8")
        self.assertIn("port=22",script)
        self.assertIn('client.connect(cfg["host"], port=22',script)
        self.assertNotIn('"ssh." + ssh_host',script)
        self.assertIn("sftp.put(",script)
        self.assertNotIn("sftp.remove(",script)

    def test_sftp_config_and_ovh_home_resolution(self):
        from scripts.deploy_atlas_sftp import configuration, target_path
        import stat
        cfg=configuration({"ATLAS_SFTP_HOST":"ftp.cluster121.hosting.ovh.net",
                           "ATLAS_SFTP_USERNAME":"user",
                           "ATLAS_SFTP_PASSWORD":"test",
                           "ATLAS_SFTP_REMOTE_DIR":"/www/atlas"})
        self.assertEqual(cfg["target"],"/www/atlas")
        class FakeSFTP:
            def normalize(self,path): return "/homez.2168/operapw"
            def stat(self,path):
                if path=="/homez.2168/operapw/www":
                    from types import SimpleNamespace
                    return SimpleNamespace(st_mode=stat.S_IFDIR | 0o755)
                raise FileNotFoundError(path)
        self.assertEqual(target_path(FakeSFTP(),cfg["target"]),
                         "/homez.2168/operapw/www/atlas")

    def test_json_only_catalog_refresh_never_triggers_ftp(self):
        workflow=(ROOT/".github/workflows/deploy-atlas.yml").read_text(encoding="utf-8")
        self.assertIn("'site/*.js'",workflow)
        self.assertIn("'site/*.html'",workflow)
        self.assertNotIn("'site/**'",workflow)
        self.assertNotIn("'site/*.json'",workflow)
        self.assertIn("if: github.ref == 'refs/heads/main'",workflow)

    @unittest.skipUnless(shutil.which("node"),"Node.js unavailable")
    def test_actual_catalog_url_builder(self):
        test=subprocess.run(["node",str(ROOT/"tests/atlas_routes_smoke.cjs")],
                            cwd=ROOT,text=True,capture_output=True)
        self.assertEqual(test.returncode,0,test.stdout+"\n"+test.stderr)

if __name__=="__main__":
    unittest.main()
