# Placa Amarela

Companion CONTROL para a Cheap Yellow Display **ESP32-2432S028R** (320×240, LVGL).

Repositório para clonar em outro PC, subir o gateway e gravar o firmware.

## O que roda em cada máquina

| Peça | Onde | Comando |
|---|---|---|
| Gateway CONTROL | PC na mesma LAN (ou Tailscale) | `python -u companion2/firmware-cyd/placa_gateway.py` |
| Firmware LVGL | placa CYD via USB | `python companion2/firmware-cyd/_build_lvgl.py --flash COMx` |
| Voz (ouvir/falar) | o mesmo PC do gateway, com o fone | `voice_pc.py` (já chamado pelo gateway) |

A placa busca `http://<ip-do-pc>:8788/cyd`. Sem o gateway, a tela sobe mas os dados não entram.

## Setup no outro PC

```powershell
git clone https://github.com/hudsonrj/placaamarela.git
cd placaamarela
pip install requests sounddevice numpy
```

Copie o token do kiosk (não vai no git):

```
companion2/firmware-cyd/.kiosk_token
```

Na máquina original o arquivo já existe. Na nova, copie do CONTROL / VPS (`KIOSK_TOKEN`) para esse caminho, uma linha só.

Suba o gateway:

```powershell
cd companion2\firmware-cyd
python -u placa_gateway.py
```

Deve escutar `0.0.0.0:8788`. Confirme:

```powershell
curl http://127.0.0.1:8788/cyd
```

A primeira linha tem que ser `CTRL/1`.

## Firmware

Arduino ESP32 3.3.x + xtensa no PATH (o script usa o pacote do Arduino15). LVGL 8.3 está em `companion2/firmware-cyd/libs/lvgl`.

```powershell
cd companion2\firmware-cyd
python _build_lvgl.py --flash COM5
```

Troque `COM5` pela porta da placa. Partição `huge_app`. Depois do flash a serial deve mostrar `BOOT CONTROL lvgl tessera`.

## O que não está no git

- `.kiosk_token`
- builds (`*.o`, pastas `build/`)
- `diario/` da SD, logs, PCM de TTS
- grafo local `graft/`

Wi-Fi da placa está no sketch (`atlas_lvgl.ino`). Se a outra rede for diferente, edite SSID/senha antes de gravar.
