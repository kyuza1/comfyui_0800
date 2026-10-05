"""Rotas no formato da OpenAI que o Open WebUI usa: conversa, modelos, imagem, voz e transcricao (com envio em pedacos)."""
import base64
import http.client
import io
import json
import os
import struct
import sys
import threading
import time
import types
import urllib.error
import urllib.request
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

m = types.ModuleType("IPython")
d = types.ModuleType("IPython.display")
d.HTML = lambda x: x
d.display = lambda *a, **k: None
d.clear_output = lambda *a, **k: None
sys.modules["IPython"] = m
sys.modules["IPython.display"] = d

FONTE = open("cell_v2.py", encoding="utf-8").read().split("# ------------------------------------------------------------------------------\n# EXECUCAO")[0]


def carrega(porta, **troca):
    src = FONTE.replace("PROTEGER_API = True #@param", "PROTEGER_API = False #@param").replace("API_PORT = 5000\n", f"API_PORT = {porta}\n")
    for a, b in {"PORT = 8188\n": "PORT = 18888\n", "VOZ_PORT = 8189\n": "VOZ_PORT = 18889\n", "OLLAMA_PORT = 11434\n": "OLLAMA_PORT = 18834\n",
                 'COMFY = "/content/ComfyUI"': 'COMFY = "t_oa"', 'VOZ_SAIDAS = "/content/voz_saidas"': 'VOZ_SAIDAS = "t_oa/falas"', **troca}.items():
        assert a in src, a
        src = src.replace(a, b)
    g = {}
    exec(src, g)
    return g


os.makedirs("t_oa/output", exist_ok=True)
from PIL import Image
buf = io.BytesIO()
Image.new("RGB", (64, 64), (10, 200, 90)).save(buf, "PNG")
PNG = buf.getvalue()
w = io.BytesIO()
wf = wave.open(w, "wb"); wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(24000)
wf.writeframes(b"".join(struct.pack("<h", int(8000 * ((i // 40) % 2 * 2 - 1))) for i in range(24000))); wf.close()
WAV = w.getvalue()
pedidos_comfy, pedidos_ollama, descarregados = [], [], []


class Falso(BaseHTTPRequestHandler):
    """Faz o papel do ComfyUI, do Ollama e do servidor de voz, conforme a porta em que foi chamado."""
    def log_message(self, *a):
        pass

    def _ok(self, corpo, tipo="application/json"):
        if isinstance(corpo, (dict, list)):
            corpo = json.dumps(corpo).encode()
        self.send_response(200); self.send_header("Content-Type", tipo); self.send_header("Content-Length", str(len(corpo))); self.end_headers(); self.wfile.write(corpo)

    def do_GET(self):
        if self.path == "/api/tags":
            self._ok({"models": [{"name": "huihui_ai/qwen3-abliterated:4b"}, {"name": "huihui_ai/qwen3-vl-abliterated:4b"}]})
        elif self.path == "/api/ps":
            self._ok({"models": [{"name": "huihui_ai/qwen3-vl-abliterated:4b"}]})
        elif self.path.startswith("/history/"):
            pid = self.path.split("/")[-1]
            n = pedidos_comfy[-1]["latente"]["inputs"]["batch_size"]
            self._ok({pid: {"status": {"status_str": "success"}, "outputs": {"salva": {"images": [{"filename": f"api_{i}.png", "subfolder": "", "type": "output"} for i in range(n)]}}}})
        elif self.path.startswith("/view"):
            self._ok(PNG, "image/png")
        else:
            self._ok({})

    def do_POST(self):
        corpo = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if self.path == "/prompt":
            pedidos_comfy.append(json.loads(corpo)["prompt"]); self._ok({"prompt_id": "0a0a0a0a-0000-0000-0000-%012d" % len(pedidos_comfy)})
        elif self.path == "/v1/chat/completions":
            j = json.loads(corpo); pedidos_ollama.append(j)
            self._ok({"choices": [{"message": {"role": "assistant", "content": "Olá!"}}], "usage": {"completion_tokens": 2}})
        elif self.path == "/api/generate":
            descarregados.append(json.loads(corpo)["model"]); self._ok({})
        elif self.path == "/falar":
            self._ok(WAV, "audio/wav")
        else:
            self._ok({})


for porta in (18888, 18889, 18834):
    threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", porta), Falso).serve_forever, daemon=True).start()
g = carrega(15040, **{"VOZ = False #@param": "VOZ = True #@param"})
g["preparar_gpu_original"] = g["preparar_gpu"]


class WhisperFalso:
    def transcribe(self, audio, language=None, beam_size=1):
        return [types.SimpleNamespace(text=f" ouvi {len(audio) / 16000:.1f} segundos de audio ")], None


g["whisper_modelo"] = WhisperFalso()
threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", 15040), g["ApiHandler"]).serve_forever, daemon=True).start()
time.sleep(0.5)
B = "http://127.0.0.1:15040"


def post(caminho, corpo):
    try:
        r = urllib.request.urlopen(urllib.request.Request(B + caminho, data=json.dumps(corpo).encode(), headers={"Content-Type": "application/json"}), timeout=120)
        return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type"), e.read()


print("modelos:", [x["id"] for x in json.loads(urllib.request.urlopen(B + "/v1/models").read())["data"]])
post("/v1/chat/completions", {"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]})
print("modelo desconhecido ->", pedidos_ollama[-1]["model"], "| primeira mensagem:", pedidos_ollama[-1]["messages"][0], "| reasoning:", pedidos_ollama[-1].get("reasoning_effort"))
post("/v1/chat/completions", {"model": "huihui_ai/qwen3-vl-abliterated:4b", "messages": [{"role": "system", "content": "Answer in English."}, {"role": "user", "content": "hi"}]})
print("modelo de visão pedido ->", pedidos_ollama[-1]["model"], "| instrução de quem chamou preservada:", [x["content"] for x in pedidos_ollama[-1]["messages"] if x["role"] == "system"])
st, ct, corpo = post("/v1/images/generations", {"model": "studio", "prompt": "a red apple", "n": 2, "size": "1024x768", "response_format": "b64_json"})
j = json.loads(corpo)
lat = pedidos_comfy[-1]["latente"]["inputs"]
print("imagens ->", st, len(j["data"]), "imagens | PNG válido:", base64.b64decode(j["data"][0]["b64_json"])[:4] == PNG[:4], f"| pedido ao ComfyUI: {lat['width']}x{lat['height']} x{lat['batch_size']}", "| descarregou do Ollama antes:", descarregados)
st, ct, corpo = post("/v1/audio/speech", {"model": "chatterbox", "input": "Olá, tudo bem?", "voice": "padrao"})
print("voz ->", st, ct, len(corpo), "bytes | é mp3:", corpo[:3] == b"ID3" or corpo[:1] == b"\xff")

limite = "----teste123"
formulario = (f"--{limite}\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\nwhisper\r\n--{limite}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"fala.wav\"\r\n"
              f"Content-Type: audio/wav\r\n\r\n").encode() + WAV + f"\r\n--{limite}--\r\n".encode()
r = urllib.request.urlopen(urllib.request.Request(B + "/v1/audio/transcriptions", data=formulario, headers={"Content-Type": f"multipart/form-data; boundary={limite}"}), timeout=120)
print("transcrição (tamanho declarado) ->", r.status, r.read().decode())
c = http.client.HTTPConnection("127.0.0.1", 15040, timeout=120)
c.putrequest("POST", "/v1/audio/transcriptions"); c.putheader("Content-Type", f"multipart/form-data; boundary={limite}"); c.putheader("Transfer-Encoding", "chunked"); c.endheaders()
for i in range(0, len(formulario), 7000):   # em pedacos, como o Open WebUI manda
    pedaco = formulario[i:i + 7000]
    c.send(f"{len(pedaco):x}\r\n".encode() + pedaco + b"\r\n")
c.send(b"0\r\n\r\n")
r = c.getresponse()
print("transcrição (em pedaços)        ->", r.status, r.read().decode())
st, ct, corpo = post("/gerar", {"prompt": "um JSON normal ainda funciona"})
print("rota antiga com JSON ->", st, ct)

for perfil, extra in [("⚡ Z Image Turbo", {"VOZ = False #@param": "VOZ = True #@param"}), ("💬 Só chat (IA sem censura, rápida)", {}), ("🎥 Vídeo (Wan 2.1)", {})]:
    h = carrega(15041, **({'PERFIL = "⚡ Z Image Turbo" #@param': f'PERFIL = "{perfil}" #@param'} if perfil != "⚡ Z Image Turbo" else {}), **extra)
    amb = h["ambiente_webui"]()
    print(f"{perfil[:18]:18s} conversa por {amb['OPENAI_API_BASE_URL']} | Ollama direto: {amb['ENABLE_OLLAMA_API']} | modelo padrão: {amb['DEFAULT_MODELS'][:34]} | imagem: {amb.get('IMAGE_GENERATION_ENGINE')} | voz: {amb.get('AUDIO_TTS_ENGINE')} | microfone: {amb.get('AUDIO_STT_ENGINE')} | MCP: {json.loads(amb['TOOL_SERVER_CONNECTIONS'])[0]['auth_type']}")
