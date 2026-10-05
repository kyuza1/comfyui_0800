"""Perfil combinado (imagem + video) com um ComfyUI falso: o mesmo /gerar escolhe o modelo certo, e a IA encadeia imagem -> video."""
import io
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

perfil = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "🎬 Imagem + Vídeo (Z Image + Wan)"
src = open("cell_v2.py", encoding="utf-8").read().split("# ------------------------------------------------------------------------------\n# EXECUCAO")[0]
for a, b in [
    ('PERFIL = "⚡ Z Image Turbo" #@param', f'PERFIL = "{perfil}" #@param'),
    ("PORT = 8188\n", "PORT = 18488\n"),
    ("API_PORT = 5000\n", "API_PORT = 15007\n"),
    ('COMFY = "/content/ComfyUI"', 'COMFY = "t_combo"'),
]:
    assert a in src, a
    src = src.replace(a, b)
g = {}
exec(src.replace("PROTEGER_API = True #@param", "PROTEGER_API = False #@param"), g)
g.update(CHAT_URL="http://127.0.0.1:18491/v1/chat/completions", CHAT_LOCAL_CPU=True, CHAT_MODO="cpu")
os.makedirs("t_combo/output", exist_ok=True)

from PIL import Image
buf = io.BytesIO()
Image.new("RGB", (1024, 1024), (30, 140, 90)).save(buf, "PNG")
PNG = buf.getvalue()
open("t_combo/output/api_00001_.png", "wb").write(PNG)
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
        pedidos.append(json.loads(self.rfile.read(n))["prompt"])
        self._send(json.dumps({"prompt_id": "c0b0c0b0-0000-0000-0000-%012d" % len(pedidos)}).encode())

    def do_GET(self):
        if self.path.startswith("/history/"):
            pid = self.path.split("/")[-1]
            wf = pedidos[int(pid[-12:]) - 1]
            video = wf["salva"]["class_type"] == "SaveWEBM"
            arq = {"filename": "api_00001_.webm" if video else "api_00001_.png", "subfolder": "", "type": "output"}
            self._send(json.dumps({pid: {"status": {"status_str": "success"}, "outputs": {"salva": {"images": [arq]}}}}).encode())
        elif self.path.startswith("/view"):
            self._send(b"\x1a\x45\xdf\xa3webm" if ".webm" in self.path else PNG, "video/webm" if ".webm" in self.path else "image/png")


class LLM(BaseHTTPRequestHandler):
    """1a chamada: gerar_imagem. Depois do resultado: gerar_video com o arquivo devolvido. Depois: texto."""
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        corpo = json.loads(self.rfile.read(n))
        ferramentas = [t["function"]["name"] for t in corpo.get("tools", [])]
        resultados = [x for x in corpo["messages"] if x["role"] == "tool"]
        if not resultados:
            msg = {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "gerar_imagem", "arguments": json.dumps({"prompt": "a green frog on a leaf"})}}]}
        elif len(resultados) == 1:
            arquivo = resultados[0]["content"].split("Arquivo: ")[1].split(" ")[0]
            msg = {"role": "assistant", "content": "", "tool_calls": [{"id": "c2", "type": "function", "function": {"name": "gerar_video", "arguments": json.dumps({"prompt": "the frog jumps away", "imagem": arquivo})}}]}
        else:
            msg = {"role": "assistant", "content": "Pronto: fiz o sapo e animei ele pulando. (ferramentas: " + ", ".join(ferramentas) + ")"}
        body = json.dumps({"choices": [{"message": msg}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


for porta, h in [(18488, Comfy), (18491, LLM), (15007, g["ApiHandler"])]:
    threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", porta), h).serve_forever, daemon=True).start()
time.sleep(0.4)
B = "http://127.0.0.1:15007"


def post(caminho, corpo):
    try:
        r = urllib.request.urlopen(urllib.request.Request(B + caminho, data=json.dumps(corpo).encode(), headers={"Content-Type": "application/json"}), timeout=60)
        return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type"), e.read()


def resumo(wf):
    lat = wf["latente"]["inputs"]
    return f"{wf['unet']['inputs']['unet_name']} | {wf['latente']['class_type']} {lat['width']}x{lat['height']} | {wf['gera']['inputs']['steps']} passos | salva com {wf['salva']['class_type']}"


print("perfil:", perfil, "| info:", urllib.request.urlopen(B + "/info").read().decode()[:120])
for rotulo, corpo in [("imagem", {"prompt": "a green frog"}), ("video do texto", {"prompt": "a frog jumping", "video": True}),
                      ("animar imagem da galeria", {"prompt": "the frog blinks", "image": "api_00001_.png"})]:
    st, ct, body = post("/gerar", corpo)
    print(f"  {rotulo:26s} -> {st} {ct} | " + (resumo(pedidos[-1]) if st == 200 else body.decode()[:120]))
if "--chat" in sys.argv:
    cid = json.loads(post("/chat", {"mensagens": [{"role": "user", "content": "faz um sapo e anima ele pulando"}]})[2])["id"]
    visto, fim = 0, False
    while not fim:
        time.sleep(0.3)
        j = json.loads(urllib.request.urlopen(f"{B}/chat/{cid}?desde={visto}").read())
        for ev in j["eventos"]:
            visto += 1
            print("  chat:", ev)
        fim = j["fim"]
    print("  o video do chat partiu de:", pedidos[-1]["inicio"]["inputs"]["image"], "| modelo", pedidos[-1]["unet"]["inputs"]["unet_name"])
tools = json.loads(post("/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})[2])["result"]["tools"]
print("  mcp:", [t["name"] for t in tools])
docs = urllib.request.urlopen(B + "/docs").read().decode()
print("  docs: campo video:", "<td>video</td>" in docs, "| exemplo com video:", '"video": true' in docs.replace("&quot;", '"'), "| generate_video:", "generate_video" in docs)

if "--servir" in sys.argv:
    # so no teste: mostra uma imagem no chat (para aparecer o link "animar") e clica nele
    g["INTERFACE_HTML"] = g["INTERFACE_HTML"].replace("</body>", "<script>setTimeout(() => { mostrarImagem('/imagem/api_00001_.png'); setTimeout(() => document.querySelector('.midia a[href=\"#\"]').click(), 400); }, 900);</script></body>")
    time.sleep(int(sys.argv[sys.argv.index("--servir") + 1]))
