"""Testa /transcrever com o Whisper tiny de verdade (CPU) e serve a pagina para a captura de tela."""
import json
import os
import sys
import threading
import time
import types
import urllib.request
from http.server import ThreadingHTTPServer

m = types.ModuleType("IPython")
d = types.ModuleType("IPython.display")
d.HTML = lambda x: x
d.display = lambda *a, **k: None
d.clear_output = lambda *a, **k: None
sys.modules["IPython"] = m
sys.modules["IPython.display"] = d

src = open("cell_v2.py", encoding="utf-8").read().split("# ------------------------------------------------------------------------------\n# EXECUCAO")[0]
for a, b in [("API_PORT = 5000\n", "API_PORT = 15003\n"), ('COMFY = "/content/ComfyUI"', 'COMFY = "t_comfy"'), ("VOZ = False #@param", "VOZ = True #@param")]:
    assert a in src, a
    src = src.replace(a, b)
g = {}
exec(src.replace("PROTEGER_API = True #@param", "PROTEGER_API = False #@param"), g)

t = time.time()
from faster_whisper import WhisperModel
g["whisper_modelo"] = WhisperModel(g["WHISPER"], device="cpu", compute_type="int8")
print(f"modelo {g['WHISPER']} carregado em {time.time() - t:.1f}s")

threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", 15003), g["ApiHandler"]).serve_forever, daemon=True).start()
time.sleep(0.5)
B = "http://127.0.0.1:15003"
for arquivo in sys.argv[1:]:
    if arquivo.startswith("--") or arquivo.isdigit() or not os.path.exists(arquivo):
        continue
    t = time.time()
    r = urllib.request.urlopen(urllib.request.Request(B + "/transcrever", data=open(arquivo, "rb").read()), timeout=300)
    print(f"{arquivo}: {r.status} em {time.time() - t:.1f}s ->", json.loads(r.read())["texto"])
print("info:", urllib.request.urlopen(B + "/info").read().decode())
if "--servir" in sys.argv:
    time.sleep(int(sys.argv[sys.argv.index("--servir") + 1]))
