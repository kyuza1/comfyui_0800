"""Perfis enxutos (so chat, so lote), chat aos poucos com raciocinio e velocidade, rota no formato da OpenAI e lotes de imagem."""
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

FONTE = open("cell_v2.py", encoding="utf-8").read().split("# ------------------------------------------------------------------------------\n# EXECUCAO")[0]
PERFIL_PADRAO = 'PERFIL = "⚡ Z Image Turbo" #@param'
CHAT_PADRAO = next(l for l in FONTE.splitlines() if l.startswith("CHAT_IA = ")).split(" #@param")[0]


def sobe(perfil, porta, chat=None, extras=()):
    src = FONTE.replace(PERFIL_PADRAO, f'PERFIL = "{perfil}" #@param').replace("PROTEGER_API = True #@param", "PROTEGER_API = False #@param")
    src = src.replace("PORT = 8188\n", "PORT = 18688\n").replace("API_PORT = 5000\n", f"API_PORT = {porta}\n").replace('COMFY = "/content/ComfyUI"', 'COMFY = "t_novos"')
    if chat:
        src = src.replace(CHAT_PADRAO, f'CHAT_IA = "{chat}"')
    for a, b in extras:
        assert a in src, a
        src = src.replace(a, b)
    g = {}
    exec(src, g)
    g.update(CHAT_URL="http://127.0.0.1:18691/v1/chat/completions")
    g["preparar_gpu"] = lambda quem: chamadas_gpu.append(quem)
    threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", porta), g["ApiHandler"]).serve_forever, daemon=True).start()
    return g


os.makedirs("t_novos/output", exist_ok=True)
from PIL import Image
buf = io.BytesIO()
Image.new("RGB", (64, 64), (200, 60, 60)).save(buf, "PNG")
PNG = buf.getvalue()
pedidos, pedidos_llm, chamadas_gpu = [], [], []
RECUSA = False


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
        pedidos.append((json.loads(self.rfile.read(n))["prompt"], time.time() + 0.6 * (len(pedidos) % 3)))   # terminam em tempos diferentes
        self._send(json.dumps({"prompt_id": "10700000-0000-0000-0000-%012d" % len(pedidos)}).encode())

    def do_GET(self):
        if self.path.startswith("/history/"):
            pid = self.path.split("/")[-1]
            wf, pronto_em = pedidos[int(pid[-12:]) - 1]
            if time.time() < pronto_em:
                return self._send(b"{}")
            n = wf["latente"]["inputs"]["batch_size"]
            imgs = [{"filename": f"api_{int(pid[-12:]):03d}_{i}.png", "subfolder": "", "type": "output"} for i in range(n)]
            self._send(json.dumps({pid: {"status": {"status_str": "success"}, "outputs": {"salva": {"images": imgs}}}}).encode())
        elif self.path.startswith("/view"):
            self._send(PNG, "image/png")
        elif self.path.startswith("/queue"):
            self._send(b'{"queue_running": [], "queue_pending": []}')


class LLM(BaseHTTPRequestHandler):
    """Imita o Ollama: responde aos poucos (SSE), com raciocinio so quando pedem, e com o uso no ultimo pedaco."""
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        corpo = json.loads(self.rfile.read(n))
        pedidos_llm.append({k: corpo.get(k) for k in ("model", "stream", "reasoning_effort", "max_tokens")} | {"tools": [t["function"]["name"] for t in corpo.get("tools", [])]})
        if RECUSA and ("tools" in corpo or "reasoning_effort" in corpo):   # modelo que nao aceita nem ferramentas nem raciocinio
            body = json.dumps({"error": {"message": ("registry model does not support tools" if "tools" in corpo else "model does not support thinking")}}).encode()
            self.send_response(400); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers()
            return self.wfile.write(body)
        pensa = corpo.get("reasoning_effort") not in (None, "none")
        quer_ferramenta = bool(corpo.get("tools")) and corpo["messages"][-1]["role"] != "tool" and "imagem" in str(corpo["messages"][-1].get("content"))
        if not corpo.get("stream"):
            body = json.dumps({"choices": [{"message": {"role": "assistant", "content": "resposta inteira"}}], "usage": {"completion_tokens": 3}}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers()
            return self.wfile.write(body)
        self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Connection", "close"); self.end_headers()

        def manda(delta=None, uso=None):
            pedaco = {"choices": [{"index": 0, "delta": delta}] if delta is not None else []}
            if uso:
                pedaco["usage"] = uso
            self.wfile.write(("data: " + json.dumps(pedaco) + "\n\n").encode()); self.wfile.flush()
        if pensa:
            for palavra in ["O ", "usuário ", "quer ", "uma ", "resposta ", "curta."]:
                manda({"content": "", "reasoning": palavra}); time.sleep(0.12)
        if quer_ferramenta:
            manda({"content": "", "tool_calls": [{"index": 0, "id": "call_1", "type": "function", "function": {"name": "gerar_imagem", "arguments": '{"prompt": "a red'}}]})
            manda({"content": "", "tool_calls": [{"index": 0, "function": {"arguments": ' apple"}'}}]})
        else:
            for palavra in ["Paris ", "é ", "a ", "capital ", "da ", "França."]:
                manda({"content": palavra}); time.sleep(0.12)
        manda(uso={"prompt_tokens": 20, "completion_tokens": 12 if pensa else 6})
        self.wfile.write(b"data: [DONE]\n\n")
        self.close_connection = True


for porta, h in [(18688, Comfy), (18691, LLM)]:
    threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", porta), h).serve_forever, daemon=True).start()


def chamar(base, caminho, corpo=None):
    try:
        r = urllib.request.urlopen(urllib.request.Request(base + caminho, data=json.dumps(corpo).encode() if corpo is not None else None, headers={"Content-Type": "application/json"}), timeout=60)
        return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type"), e.read()


def conversa(base, texto, pensar=False):
    cid = json.loads(chamar(base, "/chat", {"mensagens": [{"role": "user", "content": texto}], "pensar": pensar})[2])["id"]
    eventos, fim = [], False
    while not fim:
        time.sleep(0.2)
        j = json.loads(chamar(base, f"/chat/{cid}?desde={len(eventos)}")[2])
        eventos += j["eventos"]
        fim = j["fim"]
    return eventos, j["novas"]


# ---------------------------------------------------------------- perfil so de chat
print("=== 💬 Só chat")
chat = sobe("💬 Só chat (IA sem censura, rápida)", 15020, extras=[("VOZ = False #@param", "VOZ = True #@param"), ("MUSICA = False #@param", "MUSICA = True #@param")])
time.sleep(0.4)
B = "http://127.0.0.1:15020"
print("extras ignorados: VOZ", chat["VOZ"], "MUSICA", chat["MUSICA"], "fundo", chat["REMOVER_FUNDO"], "whisper", chat["WHISPER"], "| modo do chat:", chat["CHAT_MODO"], "| max_tokens:", chat["CHAT_MAX_TOKENS"])
print("etapas:", [k for k in chat["estado"]])
print("info:", chamar(B, "/info")[2].decode()[:150])
ev, novas = conversa(B, "Qual é a capital da França?")
print("sem pensar ->", [e["tipo"] for e in ev], "| final:", [e["texto"] for e in ev if e["tipo"] == "texto"], "| velocidade:", [e for e in ev if e["tipo"] == "velocidade"])
print("   pedido à IA:", pedidos_llm[-1], "| pediu a GPU a alguém:", chamadas_gpu)
ev, novas = conversa(B, "Qual é a capital da França?", pensar=True)
print("pensando   ->", [e["tipo"] for e in ev], "| último pensamento:", [e["texto"] for e in ev if e["tipo"] == "pensamento"][-1:], "| reasoning_effort:", pedidos_llm[-1]["reasoning_effort"])
st, ct, corpo = chamar(B, "/v1/chat/completions", {"model": "gpt-4o", "messages": [{"role": "user", "content": "oi"}]})
print("/v1/chat/completions (inteira) ->", st, ct, corpo.decode()[:80], "| modelo repassado:", pedidos_llm[-1]["model"], "| reasoning_effort:", pedidos_llm[-1]["reasoning_effort"])
st, ct, corpo = chamar(B, "/v1/chat/completions", {"model": "x", "stream": True, "messages": [{"role": "user", "content": "oi"}]})
print("/v1/chat/completions (aos poucos) ->", st, ct, "| pedaços:", corpo.count(b"data: "), "| termina com DONE:", corpo.strip().endswith(b"[DONE]"))
print("/v1/models ->", chamar(B, "/v1/models")[2].decode())
print("pedir imagem neste perfil ->", chamar(B, "/gerar", {"prompt": "x"})[2].decode()[:90])
print("mcp:", [t["name"] for t in json.loads(chamar(B, "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})[2])["result"]["tools"]], "| docs tem Imagem:", "id='Imagem'" in chamar(B, "/docs")[2].decode(), "| docs tem /v1:", "/v1/chat/completions" in chamar(B, "/docs")[2].decode())

# ---------------------------------------------------------------- perfil so de lote
print("=== 🖼️ Só imagens em lote")
lote = sobe("🖼️ Só imagens em lote (SDXL Lightning)", 15021)
time.sleep(0.4)
B = "http://127.0.0.1:15021"
print("chat:", lote["CHAT_LIGADO"], "| etapas:", list(lote["estado"]), "| lote máximo:", lote["LOTE_MAXIMO"])
pedidos.clear()
st, ct, corpo = chamar(B, "/lote", {"prompts": ["a red fox", "a blue bird"], "quantidade": 10, "seed": 100})
j = json.loads(corpo)
print("POST /lote ->", st, j["total"], "imagens |", len(pedidos), "pedidos ao ComfyUI, tamanhos:", [w["latente"]["inputs"]["batch_size"] for w, _ in pedidos], "| seeds:", [w["gera"]["inputs"]["seed"] for w, _ in pedidos])
ks = pedidos[0][0]["gera"]["inputs"]
print("   sampler:", ks["steps"], "passos, cfg", ks["cfg"], ks["sampler_name"], ks["scheduler"], "| checkpoint:", pedidos[0][0]["ckpt"]["inputs"]["ckpt_name"])
vistas = []
while True:
    a = json.loads(chamar(B, "/lote/" + j["id"])[2])
    if len(a["prontas"]) not in vistas:
        vistas.append(len(a["prontas"]))
    if a["fim"]:
        break
    time.sleep(0.2)
print("acompanhando: prontas ao longo do tempo", vistas, "| total final", len(a["prontas"]), "| exemplo de endereço:", a["imagens"][0], "| erros:", a["erros"])
st, ct, corpo = chamar(B, "/gerar", {"prompt": "one"})
print("uma imagem só (/gerar) ->", st, ct, "| batch:", pedidos[-1][0]["latente"]["inputs"]["batch_size"])
print("lote grande demais ->", chamar(B, "/lote", {"prompts": ["a"] * 5, "quantidade": 64})[2].decode()[:80])

# ---------------------------------------------------------------- modos do chat num perfil normal
print("=== modos do chat (perfil Z Image)")
for rotulo in ["🧠 Qwen3 4B sem censura (GPU, reveza com a imagem)", "⚡ Qwen3 1.7B sem censura (GPU, fica carregada)", "🪶 Qwen3 0.6B sem censura (CPU, a mais leve)"]:
    g = sobe("⚡ Z Image Turbo", 15022 + ["🧠", "⚡", "🪶"].index(rotulo[0]), chat=rotulo)
    time.sleep(0.3)
    chamadas_gpu.clear()
    ev, _ = conversa(f"http://127.0.0.1:{g['API_PORT']}", "faz uma imagem de uma maçã")
    print(f"{rotulo[:16]:16s} modo {g['CHAT_MODO']:6s} | eventos {[e['tipo'] for e in ev if e['tipo'] != 'parcial']} | prompt da ferramenta: {[e['resumo'] for e in ev if e['tipo'] == 'ferramenta']} | pediu a GPU: {sorted(set(chamadas_gpu))}")
z = g
pedidos.clear()
st, ct, corpo = chamar(f"http://127.0.0.1:{z['API_PORT']}", "/lote", {"prompt": "a cat", "quantidade": 6})
print("lote no Z Image ->", st, [w["latente"]["inputs"]["batch_size"] for w, _ in pedidos], "(máximo", z["LOTE_MAXIMO"], "por vez)")
RECUSA = True
pedidos_llm.clear()
ev, _ = conversa(f"http://127.0.0.1:{z['API_PORT']}", "faz uma imagem de uma maçã")
print("modelo que recusa ferramentas e raciocínio ->", [e["tipo"] for e in ev if e["tipo"] != "parcial"], "| tentativas:", [(bool(x["tools"]), x["reasoning_effort"]) for x in pedidos_llm], "| aprendeu:", sorted(z["chat_recusa"]))
pedidos_llm.clear(); conversa(f"http://127.0.0.1:{z['API_PORT']}", "oi")
print("   chamada seguinte já vai sem os dois ->", [(bool(x["tools"]), x["reasoning_effort"]) for x in pedidos_llm])
RECUSA = False
print("opções de CHAT_IA:", [(k[:22], v[0][:48], v[1], v[2]) for k, v in z["CHAT_LOCAIS"].items()])
if "--servir" in sys.argv:
    chat["INTERFACE_HTML"] = chat["INTERFACE_HTML"].replace("</body>", "<script>setTimeout(() => { $('pensar').click(); $('msg').value = 'Qual é a capital da França?'; $('form').requestSubmit(); }, 1200);</script></body>")
    z["INTERFACE_HTML"] = z["INTERFACE_HTML"].replace("</body>", "<script>setTimeout(() => { $('i-prompt').value = 'a red apple'; $('i-qtd').value = '6'; $('i-gerar').click(); }, 1200);</script></body>")
    print("servindo: chat", 15020, "| z image", z["API_PORT"], flush=True)
    time.sleep(int(sys.argv[sys.argv.index("--servir") + 1]))
