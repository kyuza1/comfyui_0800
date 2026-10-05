"""Chat formatado: uma IA de mentira responde em Markdown com codigo; testa o parar pela API e serve a pagina para a captura."""
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
for a, b in [('PERFIL = "⚡ Z Image Turbo" #@param', 'PERFIL = "💬 Só chat (IA sem censura, rápida)" #@param'), ("PROTEGER_API = True #@param", "PROTEGER_API = False #@param"),
             ("API_PORT = 5000\n", "API_PORT = 15030\n"), ("PORT = 8188\n", "PORT = 18788\n")]:
    assert a in src, a
    src = src.replace(a, b)
g = {}
exec(src, g)
g.update(CHAT_URL="http://127.0.0.1:18791/v1/chat/completions")

RESPOSTA = """Claro! Aqui vai uma função em **Python** que soma uma lista, usando `sum`:

```python
def somar(numeros):
    \"\"\"Devolve a soma de uma lista de números.\"\"\"
    return sum(numeros)

print(somar([1, 2, 3]))  # 6
```

### Como usar

1. Copie o código com o botão **copiar**
2. Rode com `python soma.py`

| Entrada | Saída |
|---|---|
| `[1, 2, 3]` | 6 |
| `[]` | 0 |

> Dica: `sum` aceita qualquer iterável. Veja a [documentação](https://docs.python.org/3/library/functions.html#sum).
"""


class LLM(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        corpo = json.loads(self.rfile.read(n))
        lento = "devagar" in str(corpo["messages"][-1].get("content"))
        self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Connection", "close"); self.end_headers()
        try:
            pedacos = [RESPOSTA[i:i + 9] for i in range(0, len(RESPOSTA), 9)]
            for p in pedacos:
                self.wfile.write(("data: " + json.dumps({"choices": [{"index": 0, "delta": {"content": p}}]}) + "\n\n").encode()); self.wfile.flush()
                time.sleep(0.25 if lento else 0.01)
            self.wfile.write(("data: " + json.dumps({"choices": [], "usage": {"completion_tokens": 180}}) + "\n\ndata: [DONE]\n\n").encode())
        except OSError:
            pass   # o cliente desistiu no meio (parar)
        self.close_connection = True


for porta, h in [(18791, LLM), (15030, g["ApiHandler"])]:
    threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", porta), h).serve_forever, daemon=True).start()
time.sleep(0.4)
B = "http://127.0.0.1:15030"


def chamar(caminho, corpo=None, metodo=None):
    r = urllib.request.urlopen(urllib.request.Request(B + caminho, data=json.dumps(corpo).encode() if corpo is not None else (b"" if metodo == "POST" else None), headers={"Content-Type": "application/json"}, method=metodo), timeout=30)
    return json.loads(r.read())


cid = chamar("/chat", {"mensagens": [{"role": "user", "content": "explique devagar"}]})["id"]
time.sleep(1.6)
print("parar ->", chamar(f"/chat/{cid}/parar", metodo="POST"))
t = time.time()
while True:
    j = chamar(f"/chat/{cid}?desde=0")
    if j["fim"]:
        break
    time.sleep(0.2)
final = [e["texto"] for e in j["eventos"] if e["tipo"] == "texto"][-1]
print(f"terminou {time.time() - t:.1f}s depois de pedir para parar | texto guardado: {len(final)} de {len(RESPOSTA)} letras | termina com: {final[-18:]!r} | historico: {[(x['role'], len(x['content'])) for x in j['novas']]}")
print("parar conversa inexistente ->", chamar("/chat/naoexiste/parar", metodo="POST"))
if "--servir" in sys.argv:
    g["INTERFACE_HTML"] = g["INTERFACE_HTML"].replace("</body>", "<script>setTimeout(() => { $('msg').value = 'Escreva uma função em Python que soma uma lista'; $('form').requestSubmit(); }, 900); setTimeout(() => { const m = $('msg'), c = getComputedStyle(m); document.title = 'medidas h=' + m.offsetHeight + ' style=' + m.style.height + ' min=' + c.minHeight + ' scroll=' + m.scrollHeight + ' w=' + m.offsetWidth; }, 2500);</script></body>")
    print("servindo", flush=True)
    time.sleep(int(sys.argv[sys.argv.index("--servir") + 1]))
