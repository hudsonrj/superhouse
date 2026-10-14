import unittest
from find_index import application_index, candidates

class IndexTests(unittest.TestCase):
    def test_active_proxy_and_environment(self):
        source = 'import os\nROOT = os.environ.get("APP_UNICA_ROOT", "/opt/app-unica")'
        self.assertEqual(application_index(source, ''), '/opt/app-unica/novo/index.html')
        self.assertEqual(application_index(source, 'APP_UNICA_ROOT=/srv/control\0SECRET=not-printed\0'), '/srv/control/novo/index.html')
        caddy = 'other.example {\nroot * /other\n}\ncontrol.ch8ai.com.br {\nhandle {\nreverse_proxy 127.0.0.1:8792\n}\n}'
        def read(file):
            self.assertEqual(file, '/srv/control/novo/index.html')
            return b'<html><title>Control</title><body></body></html>'
        self.assertEqual(candidates(caddy, read, application_index(source, 'APP_UNICA_ROOT=/srv/control')), ['/srv/control/novo/index.html'])
    def test_only_control_site_root(self):
        caddy = 'other.example {\nroot * /other\n}\ncontrol.ch8ai.com.br {\nroot * /var/www/control-kiosk\ntry_files {path} /index.html\n}'
        self.assertEqual(candidates(caddy, lambda _: b'<body>CONTROL</body>'), ['/var/www/control-kiosk/index.html'])
    def test_missing_or_invalid_file_not_selected(self):
        caddy = 'control.ch8ai.com.br {\nroot * /bad\n}'
        self.assertEqual(candidates(caddy, lambda _: b'not html'), [])
        def missing(_):
            raise FileNotFoundError()
        self.assertEqual(candidates(caddy, missing), [])
        self.assertIsNone(application_index('ROOT = "/different/app"', ''))

if __name__ == '__main__':
    unittest.main()
