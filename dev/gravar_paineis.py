"""Grava GIFs dos paineis de verdade do notebook (o de escolher o pack e o de instalacao), para o README.

Rode de dentro da pasta dev:  python gravar_paineis.py
Precisa do Playwright (pip install playwright && playwright install chromium). Os GIFs vao para ../docs/gifs.
O codigo da celula e executado fora do Colab (com o IPython de mentira, como nos testes) e o HTML que ele gera e
fotografado num Chromium sem janela, quadro a quadro.
"""
import io
import json
import os
import sys
import time
import types

from PIL import Image
from playwright.sync_api import sync_playwright

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "..", "docs", "gifs")
LARGURA = 1000

m = types.ModuleType("IPython")
d = types.ModuleType("IPython.display")
d.HTML = lambda x: x
d.display = lambda *a, **k: None
d.clear_output = lambda *a, **k: None
sys.modules["IPython"] = m
sys.modules["IPython.display"] = d

FONTE = open(os.path.join(AQUI, "studio_cell.py"), encoding="utf-8").read()
FONTE = FONTE.split("# ------------------------------------------------------------------------------\n# EXECUCAO")[0]

CURSOR = """<div id="cursor-falso" style="position:fixed;left:-50px;top:-50px;z-index:99;pointer-events:none;transition:left .35s,top .35s">
<svg width="22" height="30" viewBox="0 0 14 22"><path d="M0 0v19l5-5 4 9 3-1-4-9h6z" fill="#000" stroke="#fff" stroke-width="1.2"/></svg></div>"""


def celula(pack_id):
    g = {"ESCOLHA_TESTE": None}
    g0 = {}
    exec(FONTE, g0)
    pack = next(p for p in g0["PACKS"] if p["id"] == pack_id)
    g["ESCOLHA_TESTE"] = dict(pack, pack=pack_id)
    exec(FONTE, g)
    return g


def salvar_gif(quadros, nome, ms=100):
    """quadros: lista de (png_bytes, quantos quadros segurar)."""
    imagens = []
    for png, segurar in quadros:
        im = Image.open(io.BytesIO(png)).convert("RGB")
        if im.width > 820:
            im = im.resize((820, round(im.height * 820 / im.width)), Image.LANCZOS)
        imagens += [im] * segurar
    altura = max(i.height for i in imagens)
    imagens = [i if i.height == altura else _completar(i, altura) for i in imagens]
    amostra = [imagens[int(k * (len(imagens) - 1) / 5)] for k in range(6)]
    mosaico = Image.new("RGB", (imagens[0].width, altura * len(amostra)))
    for k, i in enumerate(amostra):
        mosaico.paste(i, (0, altura * k))
    paleta = mosaico.quantize(255, method=Image.Quantize.MEDIANCUT)
    finais = [i.quantize(palette=paleta, dither=Image.Dither.NONE) for i in imagens]
    os.makedirs(SAIDA, exist_ok=True)
    caminho = os.path.join(SAIDA, nome)
    finais[0].save(caminho, save_all=True, append_images=finais[1:], duration=ms, loop=0, optimize=True)
    print(f"{nome}: {len(finais)} quadros, {os.path.getsize(caminho) / 1024:.0f} KB")


def _completar(im, altura):
    novo = Image.new("RGB", (im.width, altura), (255, 255, 255))
    novo.paste(im, (0, 0))
    return novo


def gravar_escolha(navegador):
    g = celula("imagem")
    dados = {"itens": g["ITENS"], "chats": g["CHATS"], "whispers": g["WHISPERS"], "limites": g["LIMITES"], "packs": g["PACKS"],
             "inicial": dict(next(p for p in g["PACKS"] if p["id"] == "imagem"), pack="imagem", proteger=True, manutencao=False)}
    pagina = navegador.new_page(viewport={"width": LARGURA, "height": 900})
    pagina.set_content("<!doctype html><meta charset=utf-8><body style='margin:0;padding:14px;background:#fff'>"
                       + g["PAINEL_ESCOLHA_HTML"].replace("__DADOS__", json.dumps(dados, ensure_ascii=False)).replace("__CRIADOR__", g["CRIADOR"]) + CURSOR)
    painel = pagina.locator("#studio-escolha")
    quadros = []

    def foto(segurar):
        quadros.append((painel.screenshot(), segurar))

    def apontar(seletor, clicar=True, segurar=6):
        caixa = pagina.locator(seletor).first.bounding_box()
        x, y = caixa["x"] + min(40, caixa["width"] / 2), caixa["y"] + caixa["height"] / 2
        pagina.evaluate(f"(() => {{const c = document.getElementById('cursor-falso'); c.style.left = '{x}px'; c.style.top = '{y}px';}})()")
        time.sleep(0.4)
        foto(3)
        if clicar:
            pagina.locator(seletor).first.click()
            time.sleep(0.3)
            foto(segurar)

    foto(10)
    apontar(".pack >> nth=0", segurar=14)                  # Influenciador
    apontar(".pack >> nth=2", segurar=12)                  # Video
    apontar(".pack >> nth=4", segurar=12)                  # Chat
    apontar(".pack >> nth=0", segurar=6)                   # volta ao Influenciador
    apontar("#se-det summary", segurar=8)                  # abre o Personalizar
    apontar("[data-k=musica]", segurar=22)                 # musica nao cabe: o painel trava
    apontar("[data-k=musica]", segurar=10)                 # tira a musica: volta a caber
    apontar("#se-iniciar", segurar=16)
    pagina.close()
    salvar_gif(quadros, "painel-escolha.gif", ms=120)


def gravar_instalacao(navegador):
    g = celula("engracado")
    est, ui = g["estado"], g["ui"]
    agora = time.time()
    g["T0"] = agora
    g["ultimas_linhas"] = lambda n=12, caminho=None: ""
    g["metricas"] = lambda: [("RAM 6.1/12.7 GB", False), ("GPU 0.3/15 GB · 0% · 41°C", False), ("disco livre 61 GB", False)]
    pagina = navegador.new_page(viewport={"width": LARGURA, "height": 900})
    quadros = []
    relogio = [0.0]

    def foto(segurar=1):
        g["time"].time = lambda: agora + relogio[0]   # o painel mostra os tempos: o relogio anda junto com o GIF
        pagina.set_content("<!doctype html><meta charset=utf-8><body style='margin:0;padding:14px;background:#fff'>"
                           "<div id=p style='display:inline-block;min-width:960px'>" + g["render"]() + "</div>")
        quadros.append((pagina.locator("#p").screenshot(), segurar))

    falsos = types.SimpleNamespace(**{k: getattr(time, k) for k in dir(time) if not k.startswith("_")})
    g["time"] = falsos
    infos = {"gpu": "Tesla T4, 15360 MiB", "comfy": "", "deps": "", "tunel": "já estava baixado", "start": "", "api": "/gerar · /mcp"}
    foto(6)
    for k in list(est):
        est[k].update(status="rodando", t0=agora + relogio[0], info="baixando..." if k.startswith("m") or "modelo" in k else "")
        passos = 5 if (k.startswith("m") or k in ("voz_inst", "voz_modelo", "deps")) else 2
        for i in range(1, passos + 1):
            relogio[0] += 7
            if passos > 2:
                est[k]["pct"] = 100 * i / passos
            foto(1)
        est[k].update(status="ok", dt=7 * passos, pct=None, info=infos.get(k, ""))
    ui.update(link="https://exemplo-comfyui.trycloudflare.com", link_api="https://exemplo-studio.trycloudflare.com",
              online=agora + relogio[0], t_fim=agora + relogio[0])
    foto(30)
    pagina.close()
    salvar_gif(quadros, "painel-instalacao.gif", ms=140)


if __name__ == "__main__":
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        gravar_escolha(navegador)
        gravar_instalacao(navegador)
        navegador.close()
