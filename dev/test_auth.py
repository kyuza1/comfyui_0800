"""API protegida: toda rota exige a chave (cabecalho, URL ou cookie), menos /health e o preflight do navegador."""
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
for a, b in [("API_PORT = 5000\n", "API_PORT = 15012\n"), ('COMFY = "/content/ComfyUI"', 'COMFY = "t_comfy"'), ("MANUTENCAO = False #@param", "MANUTENCAO = True #@param"),
             ("VOZ = False #@param", "VOZ = True #@param"), ("MUSICA = False #@param", "MUSICA = True #@param"), ("EFEITOS = False #@param", "EFEITOS = True #@param")]:
    assert a in src, a
    src = src.replace(a, b)
g = {}
exec(src, g)   # este teste roda com PROTEGER_API ligado, o padrao
CHAVE, SENHA = g["CHAVE_API"], g["SENHA_MANUTENCAO"]
g["ui"].update(link="https://comfy.trycloudflare.com", link_api="http://127.0.0.1:15012", online=time.time(), t_fim=time.time())
threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", 15012), g["ApiHandler"]).serve_forever, daemon=True).start()
time.sleep(0.4)
B = "http://127.0.0.1:15012"


class SemRedirecionar(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


abridor = urllib.request.build_opener(SemRedirecionar)


def chamar(metodo, caminho, cabecalhos=None, corpo=None):
    req = urllib.request.Request(B + caminho, data=corpo, headers=cabecalhos or {}, method=metodo)
    try:
        r = abridor.open(req, timeout=30)
        return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


print("chave:", CHAVE[:10] + "...", f"({len(CHAVE)} caracteres)")
# 1. todas as rotas que o handler conhece, sem chave: so /health pode responder
handler = fonte[fonte.index("class ApiHandler"):fonte.index("def abrir_tunel")]
get_, post_ = handler[handler.index("def do_GET"):handler.index("def do_POST")], handler[handler.index("def do_POST"):]
rotas = [("GET", r) for r in sorted(set(re.findall(r'caminho == "(/?[\w./-]*)"', get_)) | {x + "x" for x in re.findall(r'caminho\.startswith\("(/[\w/-]+/)"\)', get_)})]
rotas += [("POST", r) for r in sorted(set(re.findall(r'caminho == "(/[\w./-]+)"', post_)) | set(re.findall(r'"(/musica|/efeito)"', post_)) | {x + "x" for x in re.findall(r'caminho\.startswith\("(/[\w/-]+/)"\)', post_)})]
abertas = []
for metodo, rota in rotas:
    st, _, _ = chamar(metodo, rota or "/", {"Content-Type": "application/json"}, b"{}" if metodo == "POST" else None)
    if st != 401:
        abertas.append((metodo, rota, st))
print(f"sem chave: {len(rotas)} rotas testadas, {len(rotas) - len(abertas)} devolveram 401 | responderam sem chave: {abertas}")
assert abertas == [("GET", "/health", 200)], abertas

# 2. as quatro formas de mandar a chave
print("Bearer certo   ->", chamar("GET", "/info", {"Authorization": "Bearer " + CHAVE})[0])
print("Bearer errado  ->", chamar("GET", "/info", {"Authorization": "Bearer " + CHAVE[:-1] + "x"})[0])
print("X-API-Key      ->", chamar("GET", "/info", {"X-API-Key": CHAVE})[0])
print("?chave= na URL ->", chamar("GET", "/info?chave=" + CHAVE)[0], "| errada:", chamar("GET", "/info?chave=nada")[0])
print("cookie         ->", chamar("GET", "/info", {"Cookie": "outra=1; studio_chave=" + CHAVE})[0])
print("preflight (OPTIONS, sem chave) ->", chamar("OPTIONS", "/gerar")[0])

# 3. o caminho do navegador: link do painel -> cookie -> pagina e chamadas sem repetir a chave
links = {rotulo: url for _, rotulo, url in g["linhas_de_conexao"]()}
print("links do painel:", {k: v.replace(CHAVE, "<chave>") for k, v in links.items()})
st, h, _ = chamar("GET", links["Studio (criar)"].replace(B, ""))
cookie = h.get("Set-Cookie", "")
print("abrir o link do Studio ->", st, "Location:", h.get("Location"), "| cookie HttpOnly:", "HttpOnly" in cookie, "SameSite:", "SameSite=Lax" in cookie)
so_cookie = {"Cookie": cookie.split(";")[0]}
st, _, corpo = chamar("GET", "/", so_cookie)
print("pagina com o cookie    ->", st, "| e o Studio:", b"comfyui-studio.exe" in corpo, "| chave no HTML do Studio:", CHAVE.encode() in corpo)
print("fetch da pagina (/info com cookie) ->", chamar("GET", "/info", so_cookie)[0], "| POST /chat com cookie ->", chamar("POST", "/chat", {**so_cookie, "Content-Type": "application/json"}, b'{"mensagens": []}')[0], "(500 = passou da porta e reclamou do corpo)")
st, _, corpo = chamar("GET", "/")
print("Studio sem chave       ->", st, "| mostra aviso amigavel:", "protegida" in corpo.decode())

# 4. documentacao e MCP ja com a chave
st, _, docs = chamar("GET", "/docs", so_cookie)
docs = docs.decode().replace("&quot;", '"')
print("docs ->", st, "| exemplos com Bearer:", docs.count('curl -H "Authorization: Bearer ' + CHAVE), "| mcp com ?chave:", f"/mcp?chave={CHAVE}" in docs, "| senha de manutencao vazou:", SENHA in docs)
st, _, spec = chamar("GET", "/openapi.json", {"Authorization": "Bearer " + CHAVE})
print("openapi security:", json.loads(spec).get("security"), "| /status:", chamar("GET", "/status", {"Authorization": "Bearer " + CHAVE})[2].decode()[:230])
st, _, r = chamar("POST", "/mcp?chave=" + CHAVE, {"Content-Type": "application/json"}, json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode())
print("mcp pela URL com chave ->", st, len(json.loads(r)["result"]["tools"]), "ferramentas | sem chave ->", chamar("POST", "/mcp", {"Content-Type": "application/json"}, b"{}")[0])

# 5. manutencao: precisa das duas coisas
corpo = json.dumps({"codigo": "print('ok')"}).encode()
print("manutencao: so a senha ->", chamar("POST", "/manutencao/exec", {"Content-Type": "application/json", "X-Senha": SENHA}, corpo)[0],
      "| so a chave ->", chamar("POST", "/manutencao/exec", {"Content-Type": "application/json", "Authorization": "Bearer " + CHAVE}, corpo)[0],
      "| as duas ->", chamar("POST", "/manutencao/exec", {"Content-Type": "application/json", "Authorization": "Bearer " + CHAVE, "X-Senha": SENHA}, corpo)[0])
painel = g["render"]()
print("painel mostra a chave:", CHAVE in painel, "| e a senha de manutencao:", SENHA in painel)
