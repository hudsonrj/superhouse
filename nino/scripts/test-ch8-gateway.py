import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
import uuid
from http.server import ThreadingHTTPServer


class GatewayTest(unittest.TestCase):
    def test_authentication_idempotency_and_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            os.environ['NINO_GATEWAY_DIR'] = directory
            Path(directory, 'token').write_text('test-token')
            spec = importlib.util.spec_from_file_location('gateway', Path(__file__).with_name('ch8-gateway.py'))
            gateway = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(gateway)
            calls = []
            gateway.run = lambda job_id, text: calls.append((job_id, text))
            server = ThreadingHTTPServer(('127.0.0.1', 0), gateway.Handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            def request(body, token='test-token'):
                req = urllib.request.Request(f'http://127.0.0.1:{server.server_port}/chat',
                    data=json.dumps(body).encode(), headers={'Authorization': 'Bearer ' + token})
                try:
                    with urllib.request.urlopen(req, timeout=5) as res:
                        return res.status, json.load(res)
                except urllib.error.HTTPError as error:
                    return error.code, json.load(error)
            try:
                body = {'requestId': str(uuid.uuid4()), 'messages': [{'role': 'user', 'content': 'oi'}]}
                self.assertEqual(request(body, 'wrong')[0], 401)
                self.assertEqual(request(body)[0], 202)
                self.assertEqual(request(body)[0], 202)
                gateway.POOL.shutdown(wait=True)
                self.assertEqual(len(calls), 1)
                body['messages'][0]['content'] = 'outro pedido'
                self.assertEqual(request(body)[0], 409)
                body['messages'] = 'malformed'
                self.assertEqual(request(body)[0], 400)
            finally:
                server.shutdown()
                server.server_close()


if __name__ == '__main__':
    unittest.main()
