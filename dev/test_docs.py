"""Serve /docs e /openapi.json com tudo ligado e confere que cada rota documentada existe de verdade no handler."""
import json
import re
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

fonte = open("cell_v2.py", encoding="utf-8").read()
src = fonte.split("# ------------------------------------------------------------------------------\n# EXECUCAO")[0]
for a, b in [("API_PORT = 5000\n", "API_PORT = 15005\n"), ("VOZ = False #@param", "VOZ = True #@param"), ('COMFY = "/content/ComfyUI"', 'COMFY = "t_comfy"')]:
    assert a in src, a
    src = src.replace(a, b)
g = {}
exec(src.replace("PROTEGER_API = True #@param", "PROTEGER_API = False #@param"), g)
g["whisper_modelo"] = object()   # so para a secao "Ouvir" aparecer
g["ui"].update(link="https://root-receive-compliant-observe.trycloudflare.com", link_api="https://library-faster-generates-particles.trycloudflare.com",
               link_colab="https://8188-gpu-t4-s-kkb-ass1a0.prod.colab.dev")
threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", 15005), g["ApiHandler"]).serve_forever, daemon=True).start()
time.sleep(0.4)
B = "http://127.0.0.1:15005"

pagina = urllib.request.urlopen(B + "/docs").read().decode()
spec = json.loads(urllib.request.urlopen(B + "/openapi.json").read())
print("docs:", len(pagina), "bytes |", pagina.count("class='cod'"), "blocos de exemplo |", pagina.count("<h3>"), "rotas na pagina")
print("openapi:", spec["openapi"], "|", len(spec["paths"]), "caminhos |", sorted(spec["paths"]))

# cada rota documentada precisa existir no codigo do handler (comparando o prefixo fixo do caminho)
handler = fonte[fonte.index("class ApiHandler"):]
for caminho, ops in spec["paths"].items():
    fixo = caminho.split("{")[0]
    achou = f'"{fixo.rstrip("/")}"' in handler or f'"{fixo}"' in handler
    print(f"  {'ok ' if achou else 'FALTA'} {','.join(ops).upper():9s} {caminho}")
    assert achou, caminho
linhas = g["linhas_de_conexao"]()
print("caixa verde:", [(r, u) for _, r, u in linhas])
if "--servir" in sys.argv:
    time.sleep(int(sys.argv[sys.argv.index("--servir") + 1]))
