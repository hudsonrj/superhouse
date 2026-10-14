import importlib.util
from pathlib import Path
import tempfile
import unittest
import uuid

spec = importlib.util.spec_from_file_location('autonomy_server', Path(__file__).with_name('server-autonomy.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class AutonomyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        module.ROOT = Path(self.directory.name)
        self.clock = module.time.time
        self.now = 1000
        module.time.time = lambda: self.now
    def tearDown(self):
        module.time.time = self.clock
        self.directory.cleanup()
    def action(self, action, request_id=None):
        return module.update({'action': action, 'requestId': request_id or str(uuid.uuid4())})
    def test_toggle_levels_and_disabled_knob(self):
        self.assertFalse(self.action('more')['enabled'])
        self.assertEqual(self.action('toggle')['level'], 0)
        self.assertEqual(self.action('more')['level'], 1)
        self.assertEqual(self.action('more')['level'], 2)
        self.assertEqual(self.action('more')['level'], 3)
        self.assertEqual(self.action('more')['level'], 3)
        self.assertEqual(self.action('less')['level'], 2)
        for _ in range(6):
            result = self.action('less')
        self.assertEqual(result['level'], -3)
        self.assertTrue(result['enabled'])
        self.assertEqual(result['scaleVersion'], 2)
        self.assertFalse(self.action('toggle')['enabled'])
        self.assertEqual(self.action('more')['level'], 0)
    def test_replay_and_lease(self):
        request_id = str(uuid.uuid4())
        first = self.action('toggle', request_id)
        self.assertEqual(self.action('toggle', request_id), first)
        with self.assertRaises(ValueError):
            self.action('more', request_id)
        self.now += 301
        self.assertFalse(module.read_state()['enabled'])
        self.assertTrue(module.read_state()['expired'])
        self.assertFalse(self.action('heartbeat')['enabled'])
        self.assertTrue(self.action('toggle')['enabled'])
    def test_invalid_inputs(self):
        for data in [None, {}, {'action': 'grant'}, {'action': 'toggle', 'requestId': 'bad'}]:
            with self.assertRaises((ValueError, KeyError, TypeError)):
                module.update(data)
    def test_route_authentication(self):
        module.TOKEN_FILE = Path(self.directory.name) / 'token'
        module.TOKEN_FILE.write_text('test-token')
        class Handler:
            headers = {}
            def _json(self, status, body):
                self.status, self.body = status, body
        handler = Handler()
        self.assertTrue(module.handle(handler, '/api/autonomy', 'POST', lambda _: {'action': 'toggle', 'requestId': str(uuid.uuid4())}))
        self.assertEqual(handler.status, 401)
        self.assertFalse(module.read_state()['enabled'])
        handler.headers = {'Authorization': 'Bearer test-token'}
        module.handle(handler, '/api/autonomy', 'POST', lambda _: {'action': 'toggle', 'requestId': str(uuid.uuid4())})
        self.assertEqual(handler.status, 200)
        self.assertTrue(handler.body['enabled'])
        self.assertFalse(module.handle(handler, '/api/other', 'GET'))

if __name__ == '__main__':
    unittest.main()
