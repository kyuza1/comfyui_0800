"""Remove o fundo de verdade (rembg + ISNet, CPU) pelas rotas da celula. Roda no venv que tem o rembg instalado."""
import base64
import io
import json
import os
import shutil
import sys
import threading
import time
import types
import urllib.error
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
for a, b in [("API_PORT = 5000\n", "API_PORT = 15009\n"), ('COMFY = "/content/ComfyUI"', 'COMFY = "t_fundo"')]:
    assert a in src, a
    src = src.replace(a, b)
g = {}
exec(src.replace("PROTEGER_API = True #@param", "PROTEGER_API = False #@param"), g)
os.makedirs("t_fundo/output", exist_ok=True)
foto = sys.argv[1]
shutil.copy(foto, "t_fundo/output/api_00001_.png")

# o removedor roda no processo proprio dele (aqui, com o Python do venv que tem o rembg), como no Colab
import subprocess
t = time.time()
open("t_fundo_server.py", "w", encoding="utf-8").write(g["FUNDO_SERVER_PY"])
trabalhador = subprocess.Popen([sys.executable, "-u", "t_fundo_server.py", "--porta", "18190"], stdout=open("t_fundo.log", "w"), stderr=subprocess.STDOUT)
g.update(FUNDO_PORT=18190)
while not g["porta_aberta"](18190):
    assert trabalhador.poll() is None, open("t_fundo.log").read()[-600:]
    time.sleep(0.3)
g["fundo_ligado"] = True
print(f"servidor do removedor no ar em {time.time() - t:.1f}s")
threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", 15009), g["ApiHandler"]).serve_forever, daemon=True).start()
time.sleep(0.4)
B = "http://127.0.0.1:15009"
from PIL import Image


def chamar(caminho, corpo, tipo=None):
    try:
        r = urllib.request.urlopen(urllib.request.Request(B + caminho, data=corpo, headers={"Content-Type": tipo} if tipo else {}), timeout=300)
        return r.status, r.headers.get("Content-Type"), r.headers.get("X-Arquivo"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type"), None, e.read()


def descreve(png):
    img = Image.open(io.BytesIO(png))
    alfa = img.getchannel("A")
    hist = alfa.histogram()
    total = img.size[0] * img.size[1]
    return f"{img.mode} {img.size}, transparente {sum(hist[:16]) / total:.0%}, opaco {sum(hist[240:]) / total:.0%}"


bruto = open(foto, "rb").read()
t = time.time()
st, ct, arq, png = chamar("/remover-fundo", bruto)
print(f"arquivo no corpo -> {st} {ct} {arq} em {time.time() - t:.1f}s | {descreve(png)}")
open("t_recorte.png", "wb").write(png)
t = time.time()
st, ct, arq, png = chamar("/remover-fundo", json.dumps({"image": "api_00001_.png"}).encode(), "application/json")
print(f"nome da galeria  -> {st} {ct} {arq} em {time.time() - t:.1f}s | {descreve(png)}")
st, ct, arq, png = chamar("/remover-fundo", json.dumps({"image": "data:image/png;base64," + base64.b64encode(bruto).decode()}).encode(), "application/json")
print(f"base64           -> {st} {ct} {arq} | {descreve(png)}")
st, ct, arq, corpo = chamar("/remover-fundo", b"isto nao e imagem")
print(f"lixo             -> {st} {corpo.decode()[:80]}")
r = json.loads(chamar("/mcp", json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "remove_background", "arguments": {"image": "api_00001_.png"}}}).encode(), "application/json")[3])["result"]
print("mcp:", [c["type"] for c in r["content"]], r["content"][0]["text"][:80])
print("galeria:", urllib.request.urlopen(B + "/galeria").read().decode()[:120])
print("info.fundo:", json.loads(urllib.request.urlopen(B + "/info").read())["fundo"], "| docs:", "/remover-fundo" in urllib.request.urlopen(B + "/docs").read().decode())

# folha de conferencia: original | recorte sobre xadrez
orig = Image.open(foto).convert("RGB").resize((512, 512))
rec = Image.open("t_recorte.png").resize((512, 512))
xadrez = Image.new("RGB", (512, 512), "white")
for y in range(0, 512, 32):
    for x in range(0, 512, 32):
        if (x // 32 + y // 32) % 2:
            xadrez.paste((200, 205, 212), (x, y, x + 32, y + 32))
xadrez.paste(rec, (0, 0), rec)
folha = Image.new("RGB", (1034, 512), "white")
folha.paste(orig, (0, 0)); folha.paste(xadrez, (522, 0))
folha.save("t_recorte_folha.png")
if "--servir" not in sys.argv:
    trabalhador.terminate()
if "--servir" in sys.argv:
    g["INTERFACE_HTML"] = g["INTERFACE_HTML"].replace("</body>", "<script>setTimeout(() => { mostrarImagem('/imagem/api_00001_.png'); setTimeout(() => [...document.querySelectorAll('.midia a')].find(a => a.textContent.includes('remover fundo')).click(), 400); }, 900);</script></body>")
    # o Studio busca a imagem original pelo ComfyUI; no teste, a rota /imagem le direto da pasta
    time.sleep(int(sys.argv[sys.argv.index("--servir") + 1]))
