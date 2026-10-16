import importlib.util
from pathlib import Path
import tempfile
import uuid
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('autonomy', Path(__file__).with_name('control-autonomy-server.py'))
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)
def action(name, cycle=None):
    data = {'action': name, 'requestId': str(uuid.uuid4())}
    if cycle: data['cycle'] = cycle
    return server.update(data)
with tempfile.TemporaryDirectory() as directory, patch.object(server, 'ROOT', Path(directory)), patch.object(server.time, 'time', return_value=1000) as clock:
    cycle = str(uuid.uuid4())
    result = action('sensor-absent', cycle)
    assert result['enabled'] and result['level'] == 0 and result['source'] == 'sensor'
    assert result['expiresAt'] == 1090
    clock.return_value = 1020
    assert action('heartbeat')['expiresAt'] == 1090
    assert action('sensor-absent', cycle)['expiresAt'] == 1110
    assert action('sensor-clear')['enabled'] is False
    assert not action('sensor-clear')['enabled']
    action('toggle'); manual = action('more')
    assert manual['level'] == 1 and manual['source'] == 'manual'
    assert action('sensor-absent', str(uuid.uuid4()))['revision'] == manual['revision']
    assert action('sensor-clear')['enabled']
    action('toggle')
    cycle = str(uuid.uuid4()); action('sensor-absent', cycle)
    action('toggle')
    assert not action('sensor-absent', cycle)['enabled'], 'Sensor ignorou desligamento manual'
    action('sensor-clear'); cycle = str(uuid.uuid4()); action('sensor-absent', cycle)
    action('more')
    assert action('sensor-clear')['enabled'], 'Retorno desfez controle manual'
    action('toggle'); action('sensor-absent', str(uuid.uuid4()))
    clock.return_value += 91
    assert not server.read_state()['enabled'], 'Lease do sensor nao expirou'
    print('Control: sensor neutro, lease, retorno e prioridade manual passaram.')
