"""Voz no headset soundcore/Q45 (nao no alto-falante do notebook)."""
from __future__ import annotations

import os
import subprocess
import tempfile
import threading
import time
import wave

LAST_PCM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_tts.pcm")


def _wav_to_pcm16(wav_path: str, pcm_path: str, rate: int = 16000) -> None:
    import numpy as np

    with wave.open(wav_path, "rb") as w:
        fs = w.getframerate()
        nch = w.getnchannels()
        sw = w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if sw != 2:
        return
    data = np.frombuffer(raw, dtype=np.int16)
    if nch > 1:
        data = data.reshape(-1, nch).mean(axis=1).astype(np.int16)
    if fs != rate and len(data) > 1:
        x = np.linspace(0, len(data) - 1, int(len(data) * rate / fs))
        data = np.interp(x, np.arange(len(data)), data.astype(np.float32)).astype(np.int16)
    with open(pcm_path, "wb") as f:
        f.write(data.tobytes())


def _sd():
    import sounddevice as sd

    return sd


def _pick(kind: str) -> int | None:
    sd = _sd()
    want = ("soundcore", "q45", "c45 note", "space q")
    skip_out = ("hands-free", "handsfree", "bthhfenum", "realtek")
    best = None
    for i, d in enumerate(sd.query_devices()):
        name = str(d.get("name") or "").lower()
        if not any(k in name for k in want):
            continue
        inn = int(d.get("max_input_channels") or 0)
        out = int(d.get("max_output_channels") or 0)
        if kind == "in" and inn > 0:
            if "headset" in name or "hands-free" in name or "handsfree" in name:
                return i
            if best is None:
                best = i
        if kind == "out" and out > 0:
            if any(s in name for s in skip_out):
                continue
            return i
    return best


_speak_lock = threading.Lock()


def _play_wav(path: str) -> None:
    import numpy as np

    sd = _sd()
    device = _pick("out")
    with wave.open(path, "rb") as w:
        fs = w.getframerate() or 22050
        nch = w.getnchannels()
        sw = w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if sw != 2 or not raw:
        return
    data = np.frombuffer(raw, dtype=np.int16)
    if nch > 1:
        data = data.reshape(-1, nch).mean(axis=1).astype(np.int16)
    target = 44100
    if fs != target and len(data) > 1:
        x = np.linspace(0, len(data) - 1, int(len(data) * target / fs))
        data = np.interp(x, np.arange(len(data)), data.astype(np.float32)).astype(np.int16)
        fs = target
    stereo = np.column_stack((data, data))
    sd.play(stereo, fs, device=device, blocking=True, latency="high")


def _sapi_wav(text: str, path: str) -> bool:
    script = (
        "Add-Type -AssemblyName System.Speech;"
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$pt = $s.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo } |"
        " Where-Object { $_.Culture.Name -like 'pt*' } | Select-Object -First 1;"
        "if ($pt) { $s.SelectVoice($pt.Name) };"
        "$s.Rate = -1;"
        f"$s.SetOutputToWaveFile('{path.replace(chr(92), '/')}');"
        "$s.Speak([Console]::In.ReadToEnd());"
        "$s.Dispose()"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            input=text[:2000].encode("utf-8"),
            timeout=90,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return os.path.isfile(path) and os.path.getsize(path) > 44
    except Exception:
        return False


def speak(text: str) -> None:
    t = (text or "").strip()
    if not t:
        return

    def _run() -> None:
        with _speak_lock:
            fd, path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            try:
                if _sapi_wav(t, path):
                    try:
                        _wav_to_pcm16(path, LAST_PCM)
                    except Exception:
                        pass
                    _play_wav(path)
            except Exception:
                pass
            try:
                os.remove(path)
            except OSError:
                pass

    threading.Thread(target=_run, daemon=True).start()


def _listen_google(seconds: int) -> str:
    try:
        import numpy as np
        from speech_recognition import AudioData, Recognizer
    except Exception:
        return ""
    sd = _sd()
    fs = 16000
    device = _pick("in")
    try:
        rec = sd.rec(
            int(seconds * fs),
            samplerate=fs,
            channels=1,
            dtype="int16",
            device=device,
        )
        sd.wait()
        audio = AudioData(np.ascontiguousarray(rec).tobytes(), fs, 2)
        return (Recognizer().recognize_google(audio, language="pt-BR") or "").strip()
    except Exception:
        return ""


def _listen_sapi(seconds: int) -> str:
    script = f"""
Add-Type -AssemblyName System.Speech
$culture = [Globalization.CultureInfo]::CreateSpecificCulture('pt-BR')
try {{ $e = New-Object Speech.Recognition.SpeechRecognitionEngine($culture) }}
catch {{ $e = New-Object Speech.Recognition.SpeechRecognitionEngine }}
try {{ $e.SetInputToDefaultAudioDevice() }} catch {{ Write-Output ''; exit 0 }}
$e.LoadGrammar((New-Object Speech.Recognition.DictationGrammar))
$e.InitialSilenceTimeout = [TimeSpan]::FromSeconds(3)
$e.BabbleTimeout = [TimeSpan]::FromSeconds(2)
$e.EndSilenceTimeout = [TimeSpan]::FromSeconds(0.9)
$r = $e.Recognize([TimeSpan]::FromSeconds({int(seconds)}))
if ($r -and $r.Text) {{ Write-Output $r.Text }}
"""
    try:
        p = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            timeout=seconds + 10,
        )
        out = (p.stdout or b"").decode("utf-8", "replace").strip()
        return out.splitlines()[-1].strip() if out else ""
    except Exception:
        return ""


def listen(seconds: int = 8) -> str:
    ev = threading.Event()

    def _prompt() -> None:
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            if _sapi_wav("pode falar", path):
                _play_wav(path)
        except Exception:
            pass
        try:
            os.remove(path)
        except OSError:
            pass
        ev.set()

    threading.Thread(target=_prompt, daemon=True).start()
    ev.wait(timeout=12)
    time.sleep(0.2)
    heard = _listen_google(seconds)
    if not heard:
        heard = _listen_sapi(seconds)
    return heard
