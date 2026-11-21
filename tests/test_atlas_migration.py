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

    def test_plain_ftp_with_existing_secret_names(self):
        script=(ROOT/"scripts/deploy_atlas.py").read_text(encoding="utf-8")
        self.assertIn("from ftplib import FTP, error_perm",script)
        self.assertIn("ftp = FTP(timeout=30",script)
        self.assertIn('ftp.login(config["username"], config["password"])',script)
        self.assertNotIn("FTP_TLS",script)
        self.assertNotIn("ftp.auth()",script)
        self.assertNotIn("ftp.prot_p()",script)
        workflow=(ROOT/".github/workflows/deploy-atlas.yml").read_text(encoding="utf-8")
        for suffix in ("HOST", "USERNAME", "PASSWORD", "REMOTE_DIR"):
            self.assertIn("secrets.ATLAS_SFTP_" + suffix,workflow)
            self.assertNotIn("secrets.ATLAS_FTP_" + suffix,workflow)
        self.assertIn("ATLAS_FTP_PORT: '21'",workflow)
        self.assertIn("ATLAS_FTP_HOST: ${{ secrets.ATLAS_SFTP_HOST }}",workflow)
        self.assertIn("scripts.deploy_atlas_simple_ftp",workflow)
        self.assertIn("apt-get install -y -qq lftp",workflow)
        self.assertNotIn("vars.ATLAS_FTPS_HOST",workflow)
        self.assertNotIn("secrets.ATLAS_SFTP_PORT",workflow)
        self.assertNotIn("ATLAS_SFTP_KNOWN_HOSTS",workflow)

    def test_json_only_catalog_refresh_never_triggers_ftp(self):
        workflow=(ROOT/".github/workflows/deploy-atlas.yml").read_text(encoding="utf-8")
        self.assertIn("'site/*.js'",workflow)
        self.assertIn("'site/*.html'",workflow)
        self.assertNotIn("'site/**'",workflow)
        self.assertNotIn("'site/*.json'",workflow)
        self.assertIn("ATLAS_DEPLOY_ENABLED",workflow)

    def test_simple_ftp_client_uses_plain_passive_mode_without_deleting(self):
        from scripts.deploy_atlas_simple_ftp import configuration, quote_lftp
        import inspect
        import scripts.deploy_atlas_simple_ftp as publisher
        code=inspect.getsource(publisher.publish)
        self.assertIn('set ftp:ssl-allow no',code)
        self.assertIn('set ftp:passive-mode yes',code)
        self.assertIn('mirror --reverse --overwrite --no-perms',code)
        self.assertNotIn('mirror --reverse --all',code)
        self.assertIn("'put ' + quote_lftp(str(folder / '.htaccess'))",code)
        self.assertNotIn('--delete',code)
        self.assertEqual(quote_lftp('a"b'), '"a\\"b"')
        host,user,password,target=configuration({
            "ATLAS_FTP_HOST":"ftp.cluster121.hosting.ovh.net",
            "ATLAS_FTP_USERNAME":"user",
            "ATLAS_FTP_PASSWORD":"password",
            "ATLAS_FTP_REMOTE_DIR":"/atlas",
        })
        self.assertEqual((host,target),("ftp.cluster121.hosting.ovh.net","/atlas"))

    def test_lftp_failure_reports_status_and_redacts_secrets(self):
        from scripts.deploy_atlas_simple_ftp import publish
        from types import SimpleNamespace
        creds={"ATLAS_FTP_HOST":"ftp.cluster121.hosting.ovh.net",
               "ATLAS_FTP_USERNAME":"exampleuser",
               "ATLAS_FTP_PASSWORD":"not-a-real-password",
               "ATLAS_FTP_REMOTE_DIR":"/atlas"}
        def fail(command, **kwargs):
            self.assertEqual(command,["lftp","-f","/dev/stdin"])
            return SimpleNamespace(returncode=1, stdout="", stderr=
                "mirror: Login failed: 530 Login authentication failed for exampleuser not-a-real-password")
        with self.assertRaises(RuntimeError) as caught:
            publish(env=creds, runner=fail)
        message=str(caught.exception)
        self.assertIn("530",message)
        self.assertIn("Login failed",message)
        self.assertNotIn(creds["ATLAS_FTP_USERNAME"],message)
        self.assertNotIn(creds["ATLAS_FTP_PASSWORD"],message)

    @unittest.skipUnless(shutil.which("node"),"Node.js unavailable")
    def test_actual_catalog_url_builder(self):
        test=subprocess.run(["node",str(ROOT/"tests/atlas_routes_smoke.cjs")],
                            cwd=ROOT,text=True,capture_output=True)
        self.assertEqual(test.returncode,0,test.stdout+"\n"+test.stderr)

if __name__=="__main__":
    unittest.main()
