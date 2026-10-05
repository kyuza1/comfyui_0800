"""Testa o perfil de animacao: fila -> 16 quadros (ComfyUI falso) -> GIF pixelado pela API."""
import io
import json
import math
import os
import sys
import threading
import time
import types
import urllib.parse
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
    ('PERFIL = "⚡ Z Image Turbo" #@param', 'PERFIL = "🕹️ Animação Pixel Art" #@param'),
    ("PORT = 8188\n", "PORT = 18288\n"),
    ("API_PORT = 5000\n", "API_PORT = 15004\n"),
    ('COMFY = "/content/ComfyUI"', 'COMFY = "t_comfy"'),
]:
    assert a in src, a
    src = src.replace(a, b)
g = {}
exec(src.replace("PROTEGER_API = True #@param", "PROTEGER_API = False #@param"), g)
os.makedirs("t_comfy/output", exist_ok=True)

from PIL import Image, ImageDraw


def quadro(i, n, w, h):
    """Bola quicando sobre um degrade: da para ver movimento e conferir a paleta."""
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = (40 + x * 60 // w, 60 + y * 120 // h, 160)
    y = h * 0.7 - abs(math.sin(i / n * math.pi * 2)) * h * 0.45
    x = w * (0.2 + 0.6 * i / n)
    ImageDraw.Draw(img).ellipse((x - 40, y - 40, x + 40, y + 40), fill=(250, 200, 60), outline=(120, 60, 20), width=6)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


pedidos = []


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
        wf = json.loads(self.rfile.read(n))["prompt"]
        pedidos.append(wf)
        self._send(json.dumps({"prompt_id": "feedbeef-0000-0000-0000-%012d" % len(pedidos)}).encode())

    def do_GET(self):
        if self.path.startswith("/history/"):
            pid = self.path.split("/")[-1]
            wf = pedidos[-1]
            n = wf["latente"]["inputs"]["length"]
            imgs = [{"filename": f"api_{i:05d}_.png", "subfolder": "", "type": "output"} for i in range(n)]
            self._send(json.dumps({pid: {"status": {"status_str": "success"}, "outputs": {"salva": {"images": imgs}}}}).encode())
        elif self.path.startswith("/view"):
            nome = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)["filename"][0]
            wf = pedidos[-1]
            lat = wf["latente"]["inputs"]
            if nome.endswith(".gif"):
                self._send(open("t_comfy/output/" + nome, "rb").read(), "image/gif")
            else:
                self._send(quadro(int(nome.split("_")[1]), lat["length"], lat["width"], lat["height"]), "image/png")


for porta, h in [(18288, Comfy), (15004, g["ApiHandler"])]:
    threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", porta), h).serve_forever, daemon=True).start()
time.sleep(0.5)
B = "http://127.0.0.1:15004"


def gerar(corpo, saida):
    r = urllib.request.urlopen(urllib.request.Request(B + "/gerar", data=json.dumps(corpo).encode(), headers={"Content-Type": "application/json"}), timeout=120)
    dados = r.read()
    open(saida, "wb").write(dados)
    gif = Image.open(io.BytesIO(dados))
    lat = pedidos[-1]["latente"]["inputs"]
    print(f"{saida}: {r.status} {r.headers.get('Content-Type')} {len(dados) / 1024:.0f} KB | arquivo {r.headers.get('X-Arquivo')} | "
          f"latente {lat['width']}x{lat['height']} x{lat['length']} | gif {gif.size} {gif.n_frames} quadros, {gif.info.get('duration')} ms/quadro, "
          f"{len(set(gif.convert('RGB').getdata()))} cores no 1o quadro")
    return r.headers.get("X-Arquivo")


arq = gerar({"prompt": "a knight walking"}, "t_anim_padrao.gif")
gerar({"prompt": "a campfire", "width": 1280, "height": 720, "frames": 12, "fps": 12, "pixels": 64, "colors": 16}, "t_anim_larga.gif")
gerar({"prompt": "sem pixelar", "pixels": 0, "frames": 8}, "t_anim_crua.gif")
wf = pedidos[0]
print("nodes:", sorted({n["class_type"] for n in wf.values()}))
print("prompt positivo:", wf["pos"]["inputs"]["text"][:90], "| modelo:", wf["unet"]["inputs"]["unet_name"], "| salva com", wf["salva"]["class_type"])
r = urllib.request.urlopen(B + "/imagem/" + arq)
print("baixar pelo /imagem:", r.status, r.headers.get("Content-Type"), "| galeria:", urllib.request.urlopen(B + "/galeria").read().decode()[:90])
st = json.loads(urllib.request.urlopen(urllib.request.Request(B + "/mcp", data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "generate_image", "arguments": {"prompt": "a cat jumping"}}}).encode(), headers={"Content-Type": "application/json"})).read())
print("mcp:", [c["type"] for c in st["result"]["content"]], st["result"]["content"][0]["text"][:80])

# folha com 4 quadros do GIF padrao, para olhar o resultado
gif = Image.open("t_anim_padrao.gif")
folha = Image.new("RGB", (gif.size[0] * 4, gif.size[1]))
for i, n in enumerate([0, 4, 8, 12]):
    gif.seek(min(n, gif.n_frames - 1))
    folha.paste(gif.convert("RGB"), (i * gif.size[0], 0))
folha.resize((folha.size[0] // 2, folha.size[1] // 2), Image.NEAREST).save("t_anim_folha.png")

st = urllib.request.urlopen(urllib.request.Request(B + "/workflow", data=json.dumps({"workflow": pedidos[0]}).encode(), headers={"Content-Type": "application/json"}))
print("POST /workflow:", st.status, st.read().decode()[:100])
open("t_comfy.log", "w", encoding="utf-8").write("linha 1\n" + chr(27) + "[32m[INFO]" + chr(27) + "[0m Starting server\n 10%|# | 1/9\r 100%|#########| 9/9 [00:14]\nultima linha\n")
g["LOG"] = "t_comfy.log"
print("GET /log:", repr(urllib.request.urlopen(B + "/log?linhas=3").read().decode()))
