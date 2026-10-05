"""Testa a interface e o chat contra uma IA falsa (formato OpenAI) e um ComfyUI falso. Deixa o servidor no ar se --servir."""
import io
import json
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
    ("PORT = 8188\n", "PORT = 18188\n"),
    ("API_PORT = 5000\n", "API_PORT = 15002\n"),
    ('COMFY = "/content/ComfyUI"', 'COMFY = "t_comfy"'),
]:
    assert a in src, a
    src = src.replace(a, b)
g = {}
exec(src.replace("PROTEGER_API = True #@param", "PROTEGER_API = False #@param"), g)
# a IA de mentira responde no lugar do Ollama; CPU=True para o teste nao pedir a GPU
g.update(CHAT_URL="http://127.0.0.1:18190/v1/chat/completions", CHAT_LOCAL_CPU=True, CHAT_MODO="cpu")

import os
from PIL import Image, ImageDraw
os.makedirs("t_comfy/output", exist_ok=True)
img = Image.new("RGB", (768, 768), (23, 45, 215))
ImageDraw.Draw(img).ellipse((180, 180, 588, 588), fill=(255, 205, 60))
buf = io.BytesIO()
img.save(buf, "PNG")
PNG = buf.getvalue()
open("t_comfy/output/api_00001_.png", "wb").write(PNG)
fila = {}
pedidos_llm = []


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
        self.rfile.read(n)
        pid = "abcdef12-0000-0000-0000-%012d" % len(fila)
        fila[pid] = time.time() + float(os.environ.get("ATRASO", "3"))
        self._send(json.dumps({"prompt_id": pid}).encode())

    def do_GET(self):
        if self.path.startswith("/history/"):
            pid = self.path.split("/")[-1]
            if pid in fila and time.time() > fila[pid]:
                self._send(json.dumps({pid: {"status": {"status_str": "success"}, "outputs": {"10": {"images": [{"filename": "api_00001_.png", "subfolder": "", "type": "output"}]}}}}).encode())
            else:
                self._send(b"{}")
        elif self.path.startswith("/view"):
            self._send(PNG, "image/png")


class LLM(BaseHTTPRequestHandler):
    """Primeira chamada: pede gerar_imagem. Depois que recebe o resultado da ferramenta: responde em texto."""
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        corpo = json.loads(self.rfile.read(n))
        pedidos_llm.append({"auth": self.headers.get("Authorization"), "n": len(corpo["messages"]), "tools": [t["function"]["name"] for t in corpo.get("tools", [])]})
        if corpo["messages"][-1]["role"] == "tool":
            msg = {"role": "assistant", "content": "Pronto! Fiz um sol amarelo sobre fundo azul."}
        else:
            msg = {"role": "assistant", "content": "Vou gerar isso para você.", "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "gerar_imagem", "arguments": json.dumps({"prompt": "a yellow sun on a deep blue background, minimal flat illustration"})}}]}
        body = json.dumps({"choices": [{"message": msg}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


for porta, h in [(18188, Comfy), (18190, LLM), (15002, g["ApiHandler"])]:
    threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", porta), h).serve_forever, daemon=True).start()
time.sleep(0.5)
B = "http://127.0.0.1:15002"


def get(path):
    r = urllib.request.urlopen(B + path, timeout=30)
    return r.status, r.headers.get("Content-Type"), r.read()


st, ct, body = get("/")
print("pagina:", st, ct, len(body), "__" not in body.decode() and "placeholders ok")
print("info:", get("/info")[2].decode())
print("galeria:", get("/galeria")[2].decode())
r = urllib.request.urlopen(urllib.request.Request(B + "/chat", data=json.dumps({"mensagens": [{"role": "user", "content": "faz um sol"}]}).encode(), headers={"Content-Type": "application/json"}))
cid = json.loads(r.read())["id"]
visto, fim = 0, False
while not fim:
    time.sleep(0.5)
    j = json.loads(get(f"/chat/{cid}?desde={visto}")[2])
    for ev in j["eventos"]:
        visto += 1
        print("  evento:", ev)
    fim = j["fim"]
print("novas mensagens:", [(x["role"], bool(x.get("tool_calls"))) for x in j["novas"]])
print("pedidos a IA:", pedidos_llm)

if "--servir" in sys.argv:
    # so no teste: a pagina manda uma mensagem sozinha, para a captura de tela mostrar uma conversa
    g["INTERFACE_HTML"] = g["INTERFACE_HTML"].replace("</body>", "<script>setTimeout(() => { $('msg').value = 'faz um sol amarelo num fundo azul'; $('form').requestSubmit(); }, 1200);</script></body>")
    print("servindo em", B, flush=True)
    time.sleep(int(sys.argv[sys.argv.index("--servir") + 1]))
