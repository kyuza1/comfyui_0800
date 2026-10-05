"""Perfil de video com um ComfyUI falso: confere tamanho/quadros pedidos, o caminho 202 -> /resultado e o tipo do arquivo."""
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

src = open("cell_v2.py", encoding="utf-8").read().split("# ------------------------------------------------------------------------------\n# EXECUCAO")[0]
for a, b in [
    ('PERFIL = "⚡ Z Image Turbo" #@param', 'PERFIL = "🎥 Vídeo (Wan 2.1)" #@param'),
    ("PORT = 8188\n", "PORT = 18388\n"),
    ("API_PORT = 5000\n", "API_PORT = 15006\n"),
    ('COMFY = "/content/ComfyUI"', 'COMFY = "t_comfy"'),
]:
    assert a in src, a
    src = src.replace(a, b)
g = {}
exec(src.replace("PROTEGER_API = True #@param", "PROTEGER_API = False #@param"), g)
esperar_original = g["esperar"]
g["esperar"] = lambda pid, limite=80: esperar_original(pid, min(limite, 2))   # no teste, o "limite do tunel" e de 2 s

WEBM = b"\x1a\x45\xdf\xa3" + b"webm-de-mentira" * 50
pedidos, prontos_em = [], {}


class Comfy(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, tipo="application/json"):
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        pedidos.append(json.loads(self.rfile.read(n))["prompt"])
        pid = "cafe0000-0000-0000-0000-%012d" % len(pedidos)
        prontos_em[pid] = time.time() + 4   # mais que o limite: forca o caminho "ainda gerando"
        self._send(json.dumps({"prompt_id": pid}).encode())

    def do_GET(self):
        if self.path.startswith("/history/"):
            pid = self.path.split("/")[-1]
            if time.time() < prontos_em.get(pid, 0):
                return self._send(b"{}")
            # formato do SaveWEBM: a lista vem em "images" e ha um "animated" que nao e arquivo
            saida = {"images": [{"filename": "api_00001_.webm", "subfolder": "", "type": "output"}], "animated": [True]}
            self._send(json.dumps({pid: {"status": {"status_str": "success"}, "outputs": {"salva": saida}}}).encode())
        elif self.path.startswith("/view"):
            self._send(WEBM, "video/webm")


for porta, h in [(18388, Comfy), (15006, g["ApiHandler"])]:
    threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", porta), h).serve_forever, daemon=True).start()
time.sleep(0.4)
B = "http://127.0.0.1:15006"


def post(corpo):
    r = urllib.request.urlopen(urllib.request.Request(B + "/gerar", data=json.dumps(corpo).encode(), headers={"Content-Type": "application/json"}), timeout=60)
    return r.status, r.headers.get("Content-Type"), r.read()


for corpo in [{"prompt": "a red fox running in snow"}, {"prompt": "waves", "width": 1280, "height": 720, "frames": 50, "fps": 24, "steps": 12}, {"prompt": "portrait", "width": 720, "height": 1280}]:
    st, ct, body = post(corpo)
    wf = pedidos[-1]
    lat, ks, sv = wf["latente"]["inputs"], wf["gera"]["inputs"], wf["salva"]["inputs"]
    print(f"POST /gerar {corpo} -> {st} {ct} | latente {lat['width']}x{lat['height']} x{lat['length']} | {ks['steps']} passos | {sv['fps']} fps")
    assert st == 202, st
    j = json.loads(body)
    caminho = j["resultado"].replace(g["base_api"](), "")
    while True:
        r = urllib.request.urlopen(B + caminho, timeout=90)
        dados = r.read()
        if r.status == 200:
            break
    print(f"   /resultado -> {r.status} {r.headers.get('Content-Type')} {len(dados)} bytes, arquivo {r.headers.get('X-Arquivo')}, assinatura webm: {dados[:4] == WEBM[:4]}")
print("nodes:", sorted({n["class_type"] for n in pedidos[0].values()}))
r = urllib.request.urlopen(B + "/imagem/api_00001_.webm")
print("GET /imagem:", r.status, r.headers.get("Content-Type"))
docs = urllib.request.urlopen(B + "/docs").read().decode()
print("docs fala em video:", "Gerar vídeo" in docs, "| video/webm:", "video/webm" in docs, "| logos:", "anthropics.png" in docs, "openai.png" in docs)
st = json.loads(urllib.request.urlopen(urllib.request.Request(B + "/mcp", data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "generate_image", "arguments": {"prompt": "a cat"}}}).encode(), headers={"Content-Type": "application/json"})).read())
print("mcp:", st["result"]["content"][0]["text"][:70])

# ---- imagem -> video
import base64, io
from PIL import Image
os.makedirs("t_comfy/output", exist_ok=True)
foto = Image.new("RGB", (900, 1600), (200, 120, 40)); buf = io.BytesIO(); foto.save(buf, "PNG")
Image.new("RGB", (1600, 900), (40, 120, 200)).save("t_comfy/output/paisagem_teste.png")
for rotulo, corpo in [("imagem inicial em base64 (retrato 900x1600)", {"prompt": "the camera slowly zooms in", "image": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}),
                      ("imagem inicial pelo nome na galeria (1600x900)", {"prompt": "clouds moving", "image": "paisagem_teste.png"}),
                      ("imagem inicial + tamanho pedido", {"prompt": "x", "image": "paisagem_teste.png", "width": 1024, "height": 1024})]:
    st, ct, body = post(corpo)
    wf = pedidos[-1]
    lat = wf["latente"]["inputs"]
    entrada = wf["inicio"]["inputs"]["image"]
    print(f"{rotulo} -> {st} | modelo {wf['unet']['inputs']['unet_name']} | {wf['latente']['class_type']} {lat['width']}x{lat['height']} x{lat['length']} | "
          f"LoadImage {entrada} existe em input: {os.path.isfile('t_comfy/input/' + entrada)} | KSampler usa {wf['gera']['inputs']['positive']}, {wf['gera']['inputs']['latent_image']}")
    for no, dados in wf.items():
        for campo, valor in dados["inputs"].items():
            if isinstance(valor, list):
                assert valor[0] in wf, (no, campo, valor)
print("texto -> video continua usando:", pedidos[0]["unet"]["inputs"]["unet_name"], pedidos[0]["latente"]["class_type"])
try:
    post({"prompt": "x", "image": "isto-nao-e-imagem"})
except urllib.error.HTTPError as e:
    print("imagem invalida ->", e.code, e.read().decode()[:110])
tool = json.loads(urllib.request.urlopen(urllib.request.Request(B + "/mcp", data=json.dumps({"jsonrpc": "2.0", "id": 9, "method": "tools/list"}).encode(), headers={"Content-Type": "application/json"})).read())["result"]["tools"][0]
print("mcp generate_image aceita:", sorted(tool["inputSchema"]["properties"]))
