"""Monta o workflow e o painel de cada perfil e confere que as ligacoes entre os nodes existem."""
import sys
import time
import types
import urllib.request

m = types.ModuleType("IPython")
d = types.ModuleType("IPython.display")
d.HTML = lambda x: x
d.display = lambda *a, **k: None
d.clear_output = lambda *a, **k: None
sys.modules["IPython"] = m
sys.modules["IPython.display"] = d

base = open("cell_v2.py", encoding="utf-8").read().split("# ------------------------------------------------------------------------------\n# EXECUCAO")[0]
paineis = []
for perfil in ["⚡ Z Image Turbo", "🎨 FLUX.2 klein", "🧍 SDXL", "👾 Pixel Art (SDXL)", "🕹️ Animação Pixel Art", "🎥 Vídeo (Wan 2.1)", "🎬 Imagem + Vídeo (Z Image + Wan)", "🎬 Imagem + Vídeo (SDXL + Wan)", "🖼️ Só imagens em lote (SDXL Lightning)"]:
    src = base.replace('PERFIL = "⚡ Z Image Turbo" #@param', f'PERFIL = "{perfil}" #@param')
    g = {}
    exec(src, g)
    wf = g["montar_workflow"]("um gato", 1024, 1024, g["PERFIL_ATUAL"]["passos"], 123)
    for no, dados in wf.items():
        for campo, valor in dados["inputs"].items():
            if isinstance(valor, list):
                assert valor[0] in wf, (perfil, no, campo, valor)
    print(perfil, "|", len(wf), "nodes |", [e[1] for e in g["ETAPAS"] if e[0].startswith("m")])
    for pasta, arquivo, url, nome, org in g["MODELOS"]:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        r = urllib.request.urlopen(req, timeout=30)
        tam = int(r.headers.get("Content-Length") or 0)
        logo_ok = urllib.request.urlopen(urllib.request.Request(f"https://github.com/{org}.png?size=64", method="HEAD"), timeout=30).status
        print(f"   {arquivo}: HTTP {r.status}, {tam / 1e9:.2f} GB, logo {org}: {logo_ok}")
    est = g["estado"]
    g["T0"] = time.time() - 95
    for k in ["gpu", "comfy", "deps", "tunel"]:
        est[k].update(status="ok", dt=3, t0=0)
    est["m0"].update(status="rodando", t0=time.time() - 20, pct=42.0, info="baixando " + g["MODELOS"][0][1], detalhe="3.10 GB de 7.40 GB · 110 MB/s · falta 0:39")
    paineis.append(g["render"]())
open("preview_perfis.html", "w", encoding="utf-8").write("<meta charset='utf-8'><body style='margin:20px;background:#fff'>" + "<div style='height:20px'></div>".join(paineis[1:]))
print("ok")
