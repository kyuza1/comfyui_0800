"""Testa a API/MCP da celula contra um ComfyUI falso, e gera o preview do painel."""
import io
import json
import sys
import threading
import time
import types
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
src = src.replace("PORT = 8188\n", "PORT = 18188\n").replace("API_PORT = 5000\n", "API_PORT = 15000\n")
g = {}
exec(src.replace("PROTEGER_API = True #@param", "PROTEGER_API = False #@param"), g)

from PIL import Image
buf = io.BytesIO()
Image.new("RGB", (1024, 1024), (23, 45, 215)).save(buf, "PNG")
PNG = buf.getvalue()
fila = {}


class Fake(BaseHTTPRequestHandler):
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
        assert wf["pos"]["inputs"]["text"]
        pid = "abcdef12-0000-0000-0000-%012d" % len(fila)
        fila[pid] = time.time() + 2
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


threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", 18188), Fake).serve_forever, daemon=True).start()
threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", 15000), g["ApiHandler"]).serve_forever, daemon=True).start()
time.sleep(0.5)
B = "http://127.0.0.1:15000"


def post(path, obj):
    r = urllib.request.urlopen(urllib.request.Request(B + path, data=json.dumps(obj).encode(), headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}))
    return r.status, r.headers.get("Content-Type"), r.read()


st, ct, body = post("/mcp", {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}})
print("initialize", st, json.loads(body)["result"]["protocolVersion"])
st, ct, body = post("/mcp", {"jsonrpc": "2.0", "method": "notifications/initialized"})
print("notification", st, len(body))
st, ct, body = post("/mcp", {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
print("tools", [t["name"] for t in json.loads(body)["result"]["tools"]])
st, ct, body = post("/mcp", {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "generate_image", "arguments": {"prompt": "a cat"}}})
res = json.loads(body)["result"]
print("call", st, [c["type"] for c in res["content"]], res["content"][0]["text"], "b64 len", len(res["content"][1]["data"]))
st, ct, body = post("/mcp", {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "generate_image", "arguments": {}}})
print("call sem prompt", json.loads(body)["result"])
st, ct, body = post("/gerar", {"prompt": "um gato", "width": 512})
print("gerar", st, ct, len(body), body[:4])
r = urllib.request.urlopen(B + "/imagem/api_00001_.png")
print("imagem", r.status, r.headers.get("Content-Type"))
print("health", urllib.request.urlopen(B + "/").read().decode()[:60])

# preview do painel
est, ui = g["estado"], g["ui"]
g["T0"] = time.time() - 260
for k, dt, info in [("gpu", 0, "Tesla T4, 15360 MiB"), ("comfy", 3, ""), ("deps", 34, ""), ("tunel", 0, ""), ("m0", 86, "8.04 GB"), ("m1", 3, "335 MB"), ("m2", 133, "12.31 GB"), ("start", 30, ""), ("api", 0, "/gerar · /mcp"), ("link", 5, "")]:
    est[k].update(status="ok", dt=dt, t0=0, info=info)
ui.update(link="https://mass-dealers-expired-borders.trycloudflare.com", link_api="https://quiet-river-sample-words.trycloudflare.com", link_colab="https://8188-gpu-t4-s-kkb-usw1b1.prod.colab.dev", online=time.time() - 62, t_fim=time.time())
g["ultimas_linhas"] = lambda n=12: "[INFO] Starting server\n[INFO] To see the GUI go to: http://0.0.0.0:8188\nloaded completely 9.5 GB\n 44%|████▍     | 4/9 [00:06<00:07,  1.5s/it]"
html_out = "<meta charset='utf-8'><body style='margin:20px;background:#fff'>" + g["render"]() + g["render_conexoes"]()
open("preview.html", "w", encoding="utf-8").write(html_out)
print("preview ok")
