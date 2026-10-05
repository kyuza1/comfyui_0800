"""Musica e efeitos com um ComfyUI falso, num perfil cujo modelo de imagem tambem mora em checkpoints (SDXL), para pegar confusao de arquivos."""
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

perfil = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "🎬 Imagem + Vídeo (SDXL + Wan)"
src = open("cell_v2.py", encoding="utf-8").read().split("# ------------------------------------------------------------------------------\n# EXECUCAO")[0]
for a, b in [
    ('PERFIL = "⚡ Z Image Turbo" #@param', f'PERFIL = "{perfil}" #@param'),
    ("MUSICA = False #@param", "MUSICA = True #@param"), ("EFEITOS = False #@param", "EFEITOS = True #@param"),
    ("PORT = 8188\n", "PORT = 18588\n"), ("API_PORT = 5000\n", "API_PORT = 15008\n"), ('COMFY = "/content/ComfyUI"', 'COMFY = "t_som"'),
]:
    assert a in src, a
    src = src.replace(a, b)
g = {}
exec(src.replace("PROTEGER_API = True #@param", "PROTEGER_API = False #@param"), g)
g.update(CHAT_URL="http://127.0.0.1:18591/v1/chat/completions", CHAT_LOCAL_CPU=True, CHAT_MODO="cpu")
os.makedirs("t_som/output", exist_ok=True)
from PIL import Image
buf = io.BytesIO()
Image.new("RGB", (64, 64), (9, 9, 9)).save(buf, "PNG")
PNG, MP3 = buf.getvalue(), b"ID3" + b"\x00" * 200
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
        self._send(json.dumps({"prompt_id": "50500000-0000-0000-0000-%012d" % len(pedidos)}).encode())

    def do_GET(self):
        if self.path.startswith("/history/"):
            pid = self.path.split("/")[-1]
            salva = pedidos[int(pid[-12:]) - 1]["salva"]
            if salva["class_type"] == "SaveAudioMP3":   # o node de audio devolve a lista na chave "audio"
                saida = {"audio": [{"filename": salva["inputs"]["filename_prefix"] + "_00001_.mp3", "subfolder": "", "type": "output"}]}
            else:
                saida = {"images": [{"filename": "api_00001_.webm" if salva["class_type"] == "SaveWEBM" else "api_00001_.png", "subfolder": "", "type": "output"}]}
            self._send(json.dumps({pid: {"status": {"status_str": "success"}, "outputs": {"salva": saida}}}).encode())
        elif self.path.startswith("/view"):
            self._send(MP3 if ".mp3" in self.path else PNG, "application/octet-stream")


class LLM(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        corpo = json.loads(self.rfile.read(n))
        if corpo["messages"][-1]["role"] == "tool":
            msg = {"role": "assistant", "content": "Pronto. Ferramentas que eu tinha: " + ", ".join(t["function"]["name"] for t in corpo.get("tools", []))}
        else:
            msg = {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "gerar_musica", "arguments": json.dumps({"prompt": "epic orchestral, drums", "segundos": 20})}}]}
        body = json.dumps({"choices": [{"message": msg}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


for porta, h in [(18588, Comfy), (18591, LLM), (15008, g["ApiHandler"])]:
    threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", porta), h).serve_forever, daemon=True).start()
time.sleep(0.4)
B = "http://127.0.0.1:15008"


def post(caminho, corpo):
    try:
        r = urllib.request.urlopen(urllib.request.Request(B + caminho, data=json.dumps(corpo).encode(), headers={"Content-Type": "application/json"}), timeout=60)
        return r.status, r.headers.get("Content-Type"), r.headers.get("X-Arquivo"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type"), None, e.read()


def confere_ligacoes(wf):
    for no, dados in wf.items():
        for campo, valor in dados["inputs"].items():
            if isinstance(valor, list) and len(valor) == 2 and isinstance(valor[0], str):
                assert valor[0] in wf, (no, campo, valor)


print("perfil:", perfil, "| baixa:", [x[1] for x in g["MODELOS"]])
st, ct, arq, body = post("/musica", {"prompt": "lofi hip hop, mellow piano", "letra": "[verse]\nola mundo", "segundos": 45})
wf = pedidos[-1]; confere_ligacoes(wf)
print(f"  /musica -> {st} {ct} {arq} mp3={body[:3] == b'ID3'} | ckpt {wf['ckpt']['inputs']['ckpt_name']} | {wf['latente']['inputs']['seconds']} s | letra {wf['pos']['inputs']['lyrics']!r} | nodes {sorted({n['class_type'] for n in wf.values()})}")
st, ct, arq, body = post("/musica", {"prompt": "ambient pads"})
print(f"  /musica sem letra -> {st} | letra {pedidos[-1]['pos']['inputs']['lyrics']!r} | {pedidos[-1]['latente']['inputs']['seconds']} s")
st, ct, arq, body = post("/efeito", {"prompt": "door creaking", "segundos": 99})
wf = pedidos[-1]; confere_ligacoes(wf)
print(f"  /efeito -> {st} {ct} {arq} | ckpt {wf['ckpt']['inputs']['ckpt_name']} | t5 {wf['clip']['inputs']['clip_name']} | {wf['latente']['inputs']['seconds']} s (pedido 99, limite 47) | nodes {sorted({n['class_type'] for n in wf.values()})}")
st, ct, arq, body = post("/gerar", {"prompt": "a cat"})
wf = pedidos[-1]
print(f"  /gerar (imagem) -> {st} {ct} | usa {wf['ckpt']['inputs']['ckpt_name'] if 'ckpt' in wf else wf['unet']['inputs']['unet_name']}")
r = urllib.request.urlopen(B + "/imagem/api_musica_00001_.mp3")
print("  baixar mp3:", r.status, r.headers.get("Content-Type"))
tools = json.loads(post("/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})[3])["result"]["tools"]
print("  mcp:", [t["name"] for t in tools])
res = json.loads(post("/mcp", {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "generate_sound_effect", "arguments": {"prompt": "rain"}}})[3])["result"]
print("  mcp efeito:", res["content"][0]["text"][:90])
cid = json.loads(post("/chat", {"mensagens": [{"role": "user", "content": "faz uma musica epica"}]})[3])["id"]
visto, fim = 0, False
while not fim:
    time.sleep(0.3)
    j = json.loads(urllib.request.urlopen(f"{B}/chat/{cid}?desde={visto}").read())
    for ev in j["eventos"]:
        visto += 1
        print("  chat:", ev)
    fim = j["fim"]
docs = urllib.request.urlopen(B + "/docs").read().decode()
print("  docs: /musica", "/musica" in docs, "| /efeito", "/efeito" in docs, "| info:", urllib.request.urlopen(B + "/info").read().decode()[:150])
print("  painel (stack):", [x for x in ["ACE-Step", "Stable Audio"] if x in g["pilha_html"]()])
if "--servir" in sys.argv:
    g["INTERFACE_HTML"] = g["INTERFACE_HTML"].replace("</body>", "<script>setTimeout(() => document.getElementById('aba-btn-som').click(), 900);</script></body>")
    time.sleep(int(sys.argv[sys.argv.index("--servir") + 1]))
