"""Janela do Control com o Electron já instalado no Nino."""
import json
import os
import queue
import secrets
import socket
import subprocess
import threading
import time
import urllib.request
import urllib.error


class ControlClient:
    def __init__(self, log):
        self.log = log
        self.commands = queue.Queue()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def send(self, command):
        self.commands.put(command)

    def close(self):
        self.commands.put(None)
        self.thread.join(timeout=25)

    def run(self):
        process = None
        endpoint = None
        token = None
        root = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(root, "control-client.log"), "ab") as output:
            while True:
                command = self.commands.get()
                if command is None:
                    if process and process.poll() is None:
                        try:
                            self.post(endpoint, token, "quit")
                        except OSError:
                            process.terminate()
                    return
                try:
                    if process is None or process.poll() is not None:
                        executable = r"C:\repositorio\nino\node_modules\electron\dist\electron.exe"
                        if not os.path.isfile(executable):
                            raise RuntimeError("Electron do Nino não encontrado.")
                        env = os.environ.copy()
                        env.pop("ELECTRON_RUN_AS_NODE", None)
                        with socket.socket() as reservation:
                            reservation.bind(("127.0.0.1", 0))
                            port = reservation.getsockname()[1]
                        token = secrets.token_urlsafe(32)
                        endpoint = f"http://127.0.0.1:{port}/command"
                        env.update(CH8_CONTROL_PORT=str(port), CH8_CONTROL_TOKEN=token)
                        process = subprocess.Popen(
                            [executable, os.path.join(root, "control", "main.js")],
                            stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                            env=env, creationflags=subprocess.CREATE_NO_WINDOW,
                        )
                        deadline = time.monotonic() + 20
                        while True:
                            try:
                                self.post(endpoint, token, "warm")
                                break
                            except urllib.error.HTTPError:
                                raise
                            except OSError:
                                if process.poll() is not None or time.monotonic() >= deadline:
                                    raise RuntimeError("A janela do Control não iniciou. Consulte control-client.log.")
                                time.sleep(0.1)
                    self.post(endpoint, token, command)
                except (OSError, RuntimeError) as error:
                    self.log(f"Falha na janela do Control: {error}")
                    if process and process.poll() is None:
                        process.terminate()
                    process = None

    @staticmethod
    def post(endpoint, token, command):
        request = urllib.request.Request(
            endpoint, data=json.dumps(command).encode(),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            if response.status != 204:
                raise RuntimeError("Resposta inválida da janela do Control.")
