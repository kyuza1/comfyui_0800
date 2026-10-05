"""Testa as rotas de voz da celula contra o servidor Chatterbox real (ja rodando em 18189) e um ComfyUI falso."""
import json
import os
import sys
import threading
import time
import types
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

m = types.ModuleType("IPython")
d = types.ModuleType("IPython.display")
d.HTML = lambda x: x
d.display = lambda *a, **k: None
d.clear_output = lambda *a, **k: None
sys.modules["IPython"] = m
sys.modules["IPython.display"] = d

aqui = os.getcwd().replace("\\", "/")
src = open("cell_v2.py", encoding="utf-8").read().split("# ------------------------------------------------------------------------------\n# EXECUCAO")[0]
for a, b in [
    ("VOZ = False #@param", "VOZ = True #@param"),
    ("PORT = 8188\n", "PORT = 18188\n"),
    ("API_PORT = 5000\n", "API_PORT = 15001\n"),
    ("VOZ_PORT = 8189\n", "VOZ_PORT = 18189\n"),
    ('VOZ_SAIDAS = "/content/voz_saidas"', f'VOZ_SAIDAS = "{aqui}/t_saidas"'),
    ('VOZ_REFS = "/content/drive/MyDrive/ComfyUI_vozes" if SALVAR_NO_DRIVE else "/content/vozes"', f'VOZ_REFS = "{aqui}/t_vozes"'),
]:
    assert a in src, a
    src = src.replace(a, b)
g = {}
exec(src.replace("PROTEGER_API = True #@param", "PROTEGER_API = False #@param"), g)
chamadas_free = []


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(n)
        chamadas_free.append(self.path)
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()


threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", 18188), Fake).serve_forever, daemon=True).start()
threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", 15001), g["ApiHandler"]).serve_forever, daemon=True).start()
time.sleep(0.5)
B = "http://127.0.0.1:15001"


def chamar(path, corpo=None, bruto=None):
    data = bruto if bruto is not None else (json.dumps(corpo).encode() if corpo is not None else None)
    try:
        r = urllib.request.urlopen(urllib.request.Request(B + path, data=data, headers={"Content-Type": "application/json"}), timeout=300)
        return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type"), e.read()


t = time.time()
st, ct, body = chamar("/falar", {"texto": "Primeiro teste pela API, com a voz padrão do modelo."})
print("falar padrao:", st, ct, len(body), body[:4], f"{time.time() - t:.1f}s", "| free chamado:", chamadas_free)
open("t_api_padrao.wav", "wb").write(body)

st, ct, body = chamar("/vozes/minha-voz", bruto=open("voz_teste2.wav", "rb").read())
print("salvar voz:", st, body.decode())
st, ct, body = chamar("/vozes")
print("listar:", body.decode())

t = time.time()
st, ct, body = chamar("/falar", {"texto": "Agora clonando a voz de referência. Funcionou?", "voz": "minha-voz"})
print("falar clonada:", st, ct, len(body), f"{time.time() - t:.1f}s")
open("t_api_clonada.wav", "wb").write(body)

st, ct, body = chamar("/falar", {"texto": "x", "voz": "nao-existe"})
print("voz inexistente:", st, body.decode()[:120])

st, ct, body = chamar("/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
print("mcp tools:", [x["name"] for x in json.loads(body)["result"]["tools"]])
st, ct, body = chamar("/mcp", {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "speak", "arguments": {"text": "Teste pelo MCP.", "voice": "minha-voz"}}})
texto = json.loads(body)["result"]["content"][0]["text"]
print("mcp speak:", texto)
url = texto.split(": ", 1)[1].replace("http://127.0.0.1:15001", "")
st, ct, body = chamar(url)
print("baixar audio:", st, ct, len(body))
st, ct, body = chamar("/mcp", {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "list_voices", "arguments": {}}})
print("mcp list_voices:", json.loads(body)["result"]["content"][0]["text"])

# imagem depois da voz deve pedir para a voz soltar a GPU
g["gpu_dono"][0] = "voz"
g["preparar_gpu"]("imagem")
print("estado da voz apos preparar_gpu('imagem'):", urllib.request.urlopen("http://127.0.0.1:18189/estado").read().decode())

# preview com voz
est, ui = g["estado"], g["ui"]
g["T0"] = time.time() - 420
for k in est:
    est[k].update(status="ok", dt=5, t0=0)
est["gpu"]["info"] = "Tesla T4, 15360 MiB"
ui.update(link="https://mass-dealers-expired-borders.trycloudflare.com", link_api="https://quiet-river-sample-words.trycloudflare.com", online=time.time() - 30, t_fim=time.time())
g["ultimas_linhas"] = lambda n=12, caminho=None: "[INFO] Starting server\n[INFO] To see the GUI go to: http://0.0.0.0:8188"
open("preview_voz.html", "w", encoding="utf-8").write("<meta charset='utf-8'><body style='margin:20px;background:#fff'>" + g["render"]() + g["render_conexoes"]())
print("pedacos:", [len(x) for x in __import__("re").split("x", "x")] and "ok")
