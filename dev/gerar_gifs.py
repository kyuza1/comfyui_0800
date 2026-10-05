"""Gera os GIFs do passo a passo do README (ilustracoes da tela, com o cursor clicando).

Rode de dentro da pasta dev:  python gerar_gifs.py
Os GIFs vao para ../docs/gifs. Sao desenhos simplificados do Drive e do Colab, nao capturas de tela:
se o formulario do notebook mudar, ajuste os textos aqui e rode de novo.
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

L, A = 820, 470          # tamanho do GIF
FPS = 14
SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "gifs")

FONTES = "C:/Windows/Fonts/"
def fonte(tam, negrito=False):
    try:
        return ImageFont.truetype(FONTES + ("segoeuib.ttf" if negrito else "segoeui.ttf"), tam)
    except OSError:
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if negrito else "DejaVuSans.ttf", tam)

F = {"p": fonte(13), "m": fonte(15), "g": fonte(19, True), "b": fonte(13, True), "mb": fonte(15, True), "t": fonte(24, True)}

BRANCO, FUNDO, LINHA = (255, 255, 255), (246, 248, 252), (218, 222, 230)
TEXTO, CINZA = (32, 33, 36), (95, 99, 104)
AZUL, AZUL_CLARO = (26, 115, 232), (211, 227, 253)
VERDE, VERDE_CLARO = (24, 128, 56), (206, 234, 214)
AMARELO, LARANJA = (251, 188, 4), (234, 134, 0)
ESCURO = (36, 41, 47)


# ------------------------------------------------------------------------------
# pecas de desenho
# ------------------------------------------------------------------------------

def caixa(d, xy, cor=BRANCO, borda=LINHA, r=8, w=1):
    d.rounded_rectangle(xy, r, fill=cor, outline=borda, width=w)


SIMBOLOS = "★✓▶▾■▮←"   # a Segoe UI nao tem esses: saem da Segoe UI Symbol
_SIMB = {}


def texto(d, xy, s, f="m", cor=TEXTO, ancora="la"):
    if not any(c in SIMBOLOS for c in s):
        d.text(xy, s, font=F[f], fill=cor, anchor=ancora)
        return
    # texto com simbolos: desenha pedaco por pedaco, cada um na fonte que tem o caractere
    fonte_txt = F[f]
    if f not in _SIMB:
        try:
            _SIMB[f] = ImageFont.truetype(FONTES + "seguisym.ttf", fonte_txt.size)
        except OSError:
            _SIMB[f] = fonte_txt
    pedacos, atual = [], ""
    for c in s:
        if (c in SIMBOLOS) != (atual[-1:] in SIMBOLOS if atual else False) and atual:
            pedacos.append(atual)
            atual = ""
        atual += c
    pedacos.append(atual)
    fontes = [_SIMB[f] if p[0] in SIMBOLOS else fonte_txt for p in pedacos]
    largura = sum(d.textlength(p, font=fo) for p, fo in zip(pedacos, fontes))
    x, y = xy
    if ancora[0] == "m":
        x -= largura / 2
    for p, fo in zip(pedacos, fontes):
        d.text((x, y), p, font=fo, fill=cor, anchor="l" + ancora[1])
        x += d.textlength(p, font=fo)


def pasta_icone(d, x, y, esc=1.0, cor=(95, 99, 104)):
    w, h = 26 * esc, 20 * esc
    d.rounded_rectangle((x, y + 4 * esc, x + w, y + h), 3, fill=cor)
    d.rounded_rectangle((x, y, x + w * 0.45, y + 8 * esc), 2, fill=cor)


def notebook_icone(d, x, y, esc=1.0):
    d.rounded_rectangle((x, y, x + 22 * esc, y + 26 * esc), 3, fill=LARANJA)
    d.ellipse((x + 4 * esc, y + 7 * esc, x + 18 * esc, y + 21 * esc), outline=BRANCO, width=max(2, int(2 * esc)))


def cursor(d, x, y, mao=False):
    pts = [(x, y), (x, y + 19), (x + 5, y + 14), (x + 9, y + 23), (x + 12, y + 22), (x + 8, y + 13), (x + 14, y + 13)]
    d.polygon(pts, fill=(0, 0, 0), outline=BRANCO)
    d.line(pts + [pts[0]], fill=BRANCO, width=1)


def clique(d, x, y, t):
    """onda do clique; t de 0 a 1"""
    r = 6 + 18 * t
    a = int(255 * (1 - t))
    d.ellipse((x - r, y - r, x + r, y + r), outline=(AZUL[0], AZUL[1], AZUL[2], a), width=3)


def legenda(d, numero, s):
    d.rectangle((0, A - 44, L, A), fill=ESCURO)
    d.ellipse((14, A - 36, 42, A - 8), fill=AZUL)
    texto(d, (28, A - 22), str(numero), "mb", BRANCO, "mm")
    texto(d, (54, A - 22), s, "mb", BRANCO, "lm")


def barra_navegador(d, url):
    d.rectangle((0, 0, L, 34), fill=(222, 225, 230))
    for i, c in enumerate([(237, 106, 94), (245, 191, 79), (98, 197, 84)]):
        d.ellipse((12 + i * 18, 11, 24 + i * 18, 23), fill=c)
    caixa(d, (80, 6, L - 20, 28), BRANCO, BRANCO, 11)
    texto(d, (96, 17), url, "p", CINZA, "lm")


# ------------------------------------------------------------------------------
# telas
# ------------------------------------------------------------------------------

def tela_drive(d, e):
    barra_navegador(d, "drive.google.com")
    d.rectangle((0, 34, L, A), fill=FUNDO)
    texto(d, (24, 52), "Drive", "t", CINZA)
    caixa(d, (20, 92, 120, 134), BRANCO, LINHA, 14)
    texto(d, (40, 113), "+  Novo", "mb", TEXTO, "lm")
    for i, (nome, ativo) in enumerate([("Meu Drive", True), ("Compartilhados", False), ("Recentes", False), ("Lixeira", False)]):
        y = 152 + i * 34
        if ativo:
            d.rounded_rectangle((14, y - 13, 170, y + 13), 13, fill=AZUL_CLARO)
        texto(d, (34, y), nome, "m", TEXTO, "lm")
    caixa(d, (184, 48, L - 14, A - 54), BRANCO, BRANCO, 14)
    caminho = "Meu Drive" + ("  ›  ComfyUI Studio" if e.get("dentro") else "")
    texto(d, (206, 76), caminho, "g")
    if not e.get("dentro"):
        itens = [("Fotos", "pasta"), ("Documentos", "pasta")] + ([("ComfyUI Studio", "pasta")] if e.get("pasta_criada") else [])
        for i, (nome, tipo) in enumerate(itens):
            x, y = 206 + i * 190, 112
            destaque = nome == "ComfyUI Studio" and e.get("destaca_pasta")
            caixa(d, (x, y, x + 176, y + 52), AZUL_CLARO if destaque else FUNDO, AZUL if destaque else LINHA, 10)
            pasta_icone(d, x + 14, y + 16)
            texto(d, (x + 50, y + 26), nome, "b", TEXTO, "lm")
    else:
        if e.get("arquivo"):
            x, y = 206, 112
            sel = e.get("arquivo_sel")
            caixa(d, (x, y, x + 230, y + 150), AZUL_CLARO if sel else FUNDO, AZUL if sel else LINHA, 10)
            d.rectangle((x + 1, y + 1, x + 229, y + 104), fill=(255, 243, 224) if not sel else (232, 240, 254))
            notebook_icone(d, x + 100, y + 36, 1.3)
            notebook_icone(d, x + 12, y + 116, 0.7)
            texto(d, (x + 36, y + 127), "comfyui_0800.ipynb", "b", TEXTO, "lm")
        else:
            d.rounded_rectangle((206, 104, L - 36, A - 76), 12, outline=AZUL if e.get("arrastando") else LINHA, width=2,
                                fill=(240, 246, 255) if e.get("arrastando") else BRANCO)
            texto(d, ((206 + L - 36) // 2, (104 + A - 76) // 2), "Arraste o arquivo para cá", "mb", AZUL if e.get("arrastando") else CINZA, "mm")
    if e.get("upload"):
        caixa(d, (L - 300, A - 120, L - 26, A - 62), ESCURO, ESCURO, 8)
        texto(d, (L - 284, A - 100), "1 upload concluído", "mb", BRANCO, "lm")
        texto(d, (L - 284, A - 79), "comfyui_0800.ipynb  ✓", "p", (180, 220, 190), "lm")
    if e.get("menu_novo"):
        caixa(d, (24, 98, 230, 214), BRANCO, LINHA, 6)
        for i, item in enumerate(["Nova pasta", "Upload de arquivo", "Upload de pasta"]):
            y = 120 + i * 34
            if e.get("menu_hover") == i:
                d.rectangle((25, y - 16, 229, y + 16), fill=(232, 234, 237))
            pasta_icone(d, 40, y - 9, 0.7) if i != 1 else notebook_icone(d, 42, y - 10, 0.7)
            texto(d, (72, y), item, "m", TEXTO, "lm")
    if e.get("dialogo_nome") is not None:
        d.rectangle((0, 34, L, A), fill=(0, 0, 0, 90))
        caixa(d, (250, 150, 590, 330), BRANCO, BRANCO, 10)
        texto(d, (276, 182), "Nova pasta", "g")
        caixa(d, (276, 210, 564, 250), BRANCO, AZUL, 4, 2)
        texto(d, (290, 230), e["dialogo_nome"] + ("|" if e.get("piscar", True) else ""), "m", TEXTO, "lm")
        texto(d, (452, 300), "Cancelar", "mb", AZUL, "mm")
        caixa(d, (500, 284, 564, 316), AZUL, AZUL, 16)
        texto(d, (532, 300), "Criar", "mb", BRANCO, "mm")
    if e.get("abrir_com"):
        caixa(d, (330, 150, 640, 290), BRANCO, LINHA, 8)
        texto(d, (350, 172), "Abrir com", "b", CINZA, "lm")
        for i, item in enumerate(["Google Colaboratory", "Conectar mais apps"]):
            y = 210 + i * 40
            if e.get("abrir_hover") == i:
                d.rectangle((331, y - 18, 639, y + 18), fill=(232, 234, 237))
            if i == 0:
                d.ellipse((350, y - 10, 370, y + 10), outline=LARANJA, width=4)
            texto(d, (384, y), item, "mb" if i == 0 else "m", TEXTO, "lm")
    if e.get("janela_arquivo"):
        caixa(d, (20, 250, 176, 400), BRANCO, LINHA, 8)
        texto(d, (34, 270), "Downloads", "b", CINZA, "lm")
        if not e.get("arrastando"):
            notebook_icone(d, 34, 292, 0.8)
            texto(d, (58, 303), "comfyui_0800", "p", TEXTO, "lm")


def tela_colab(d, e):
    barra_navegador(d, "colab.research.google.com")
    d.rectangle((0, 34, L, A), fill=BRANCO)
    d.ellipse((16, 44, 46, 64), outline=LARANJA, width=5)
    texto(d, (58, 50), "comfyui_0800.ipynb", "mb", TEXTO, "lm")
    menus = ["Arquivo", "Editar", "Ver", "Inserir", "Ambiente de execução", "Ferramentas", "Ajuda"]
    x = 58
    posicoes = {}
    for m in menus:
        w = d.textlength(m, font=F["p"])
        if e.get("menu_aberto") == m:
            d.rounded_rectangle((x - 6, 62, x + w + 6, 84), 4, fill=(232, 234, 237))
        texto(d, (x, 73), m, "p", TEXTO, "lm")
        posicoes[m] = x
        x += w + 16
    # conexao no canto
    if e.get("gpu"):
        caixa(d, (L - 176, 50, L - 14, 80), BRANCO, LINHA, 15)
        d.ellipse((L - 164, 59, L - 152, 71), fill=VERDE)
        texto(d, (L - 144, 65), "T4  RAM ▮▮ Disco ▮", "p", TEXTO, "lm")
    else:
        caixa(d, (L - 130, 50, L - 20, 80), BRANCO, LINHA, 15)
        texto(d, (L - 75, 65), "Conectar  ▾", "b", AZUL, "mm")
    d.line((0, 92, L, 92), fill=LINHA)
    # celula com o formulario
    caixa(d, (20, 104, L - 20, 260 if not e.get("painel") else 160), (248, 249, 250), LINHA, 6)
    play_cor = AZUL if not e.get("rodando") else (217, 48, 37)
    d.ellipse((32, 116, 62, 146), fill=play_cor)
    if e.get("rodando"):
        d.rectangle((41, 125, 53, 137), fill=BRANCO)
    else:
        d.polygon([(43, 122), (43, 140), (56, 131)], fill=BRANCO)
    texto(d, (78, 131), "🚀 ComfyUI Studio".replace("🚀 ", ""), "g", TEXTO, "lm")
    if not e.get("painel"):
        texto(d, (78, 164), "Aperte o ▶ ao lado do título. Vai aparecer um painel", "p", CINZA, "lm")
        texto(d, (78, 184), "para escolher o pack e depois é só clicar em Iniciar.", "p", CINZA, "lm")
        texto(d, (78, 230), "SALVAR_NO_DRIVE:", "mb", TEXTO, "lm")
        d.rounded_rectangle((226, 220, 246, 240), 3, fill=AZUL)
        d.line([(230, 230), (235, 235), (243, 224)], fill=BRANCO, width=3)
    elif e.get("painel") == "escolha":
        painel_escolha(d, e)
    else:
        painel_instalacao(d, e)
    # menu Ambiente de execucao
    if e.get("menu_aberto") == "Ambiente de execução":
        x0 = posicoes["Ambiente de execução"] - 6
        itens = ["Executar tudo", "Interromper execução", "Reiniciar sessão", "Alterar o tipo de ambiente de execução", "Desconectar e excluir ambiente"]
        caixa(d, (x0, 86, x0 + 320, 86 + 36 * len(itens) + 8), BRANCO, LINHA, 6)
        for i, item in enumerate(itens):
            y = 108 + i * 36
            if e.get("menu_hover") == i:
                d.rectangle((x0 + 1, y - 17, x0 + 319, y + 17), fill=(232, 234, 237))
            texto(d, (x0 + 18, y), item, "m", TEXTO, "lm")
    if e.get("dialogo_t4"):
        d.rectangle((0, 34, L, A), fill=(0, 0, 0, 90))
        caixa(d, (230, 100, 590, 380), BRANCO, BRANCO, 10)
        texto(d, (256, 132), "Alterar o tipo de ambiente", "g")
        texto(d, (256, 168), "Acelerador de hardware", "b", CINZA, "lm")
        for i, op in enumerate(["CPU", "T4 GPU", "v2-8 TPU"]):
            y = 204 + i * 38
            marcado = (op == "T4 GPU" and e.get("t4_marcado")) or (op == "CPU" and not e.get("t4_marcado"))
            d.ellipse((258, y - 9, 276, y + 9), outline=AZUL if marcado else CINZA, width=2)
            if marcado:
                d.ellipse((263, y - 4, 271, y + 4), fill=AZUL)
            texto(d, (290, y), op, "mb" if op == "T4 GPU" else "m", TEXTO, "lm")
            if op == "T4 GPU":
                texto(d, (370, y), "← essa!", "b", VERDE, "lm")
        texto(d, (456, 346), "Cancelar", "mb", AZUL, "mm")
        caixa(d, (502, 330, 570, 362), AZUL, AZUL, 16)
        texto(d, (536, 346), "Salvar", "mb", BRANCO, "mm")
    if e.get("aviso"):
        d.rectangle((0, 34, L, A), fill=(0, 0, 0, 90))
        caixa(d, (190, 120, 630, 340), BRANCO, BRANCO, 10)
        texto(d, (216, 152), "Aviso: este notebook não é do Google", "g")
        for i, linha in enumerate(["Ele foi criado por outra pessoa. É normal aparecer", "esta mensagem: o código está aberto no GitHub."]):
            texto(d, (216, 190 + i * 22), linha, "m", CINZA, "lm")
        texto(d, (430, 306), "Cancelar", "mb", AZUL, "mm")
        texto(d, (544, 306), "Executar assim mesmo", "mb", AZUL, "mm")


def painel_escolha(d, e):
    """Versao resumida do painel de escolha do pack (o de verdade esta no GIF painel-escolha.gif)."""
    caixa(d, (20, 170, L - 20, A - 54), BRANCO, (87, 96, 106), 0)
    d.rectangle((21, 171, L - 21, 192), fill=(243, 244, 246))
    texto(d, (34, 182), "Prompt de Comando · comfyui-setup.exe", "p", TEXTO, "lm")
    texto(d, (38, 212), "Escolha o pack", "mb", (23, 45, 215), "lm")
    nomes = ["Influenciador Engraçado", "Influenciador Hot (+18)", "Imagem", "Vídeo", "Áudio e voz", "Chat sem censura"]
    for i, nome in enumerate(nomes):
        x, y = 38 + (i % 3) * 250, 232 + (i // 3) * 62
        sel = i == e.get("pack_sel", 2)
        caixa(d, (x, y, x + 236, y + 52), (243, 245, 255) if sel else BRANCO, (23, 45, 215) if sel else LINHA, 0, 2 if sel else 1)
        texto(d, (x + 10, y + 16), nome, "b", TEXTO, "lm")
        if True:
            texto(d, (x + 10, y + 36), "★ recomendado na T4", "p", VERDE, "lm")
    caixa(d, (38, 366, 140, 396), (23, 45, 215), (23, 45, 215), 0)
    texto(d, (89, 381), "Iniciar >", "mb", BRANCO, "mm")


def painel_instalacao(d, e):
    caixa(d, (20, 170, L - 20, A - 54), BRANCO, (87, 96, 106), 0)
    d.rectangle((21, 171, L - 21, 192), fill=(243, 244, 246))
    texto(d, (34, 182), "Prompt de Comando · comfyui-setup.exe", "p", TEXTO, "lm")
    texto(d, (40, 222), "COMFYUI", "t", (23, 45, 215), "lm")
    etapas = ["Verificar GPU", "Baixar modelos", "Instalar extras", "Iniciar", "Criar links"]
    p = e.get("progresso", 0)
    for i, nome in enumerate(etapas):
        y = 262 + i * 24
        feito = min(1, max(0, p * len(etapas) - i))
        cor = VERDE if feito >= 1 else ((23, 45, 215) if feito > 0 else (140, 147, 156))
        texto(d, (40, y), ("✓ " if feito >= 1 else "• ") + nome, "p", cor, "lm")
        d.rectangle((220, y - 4, 520, y + 4), fill=(225, 228, 232))
        if feito > 0:
            d.rectangle((220, y - 4, 220 + int(300 * feito), y + 4), fill=cor)
    if p >= 1:
        caixa(d, (540, 252, L - 36, 370), (240, 255, 244), VERDE, 0, 2)
        texto(d, (556, 276), "Pronto!", "g", VERDE, "lm")
        texto(d, (556, 306), "> Abrir o Studio", "mb", TEXTO, "lm")
        texto(d, (556, 334), "> Abrir o ComfyUI", "mb", TEXTO, "lm")


# ------------------------------------------------------------------------------
# motor de animacao: cada GIF e uma lista de passos
# ------------------------------------------------------------------------------

class Filme:
    def __init__(self, tela, estado, cursor_xy=(L // 2, A // 2)):
        self.tela, self.e, self.cur = tela, dict(estado), cursor_xy
        self.quadros = []
        self.onda = None
        self.leg = (1, "")
        self.arrasto = None

    def legenda(self, n, s):
        self.leg = (n, s)

    def _quadro(self):
        im = Image.new("RGB", (L, A), BRANCO)   # RGB: as cores com transparencia se misturam ao fundo
        d = ImageDraw.Draw(im, "RGBA")
        self.tela(d, self.e)
        if self.arrasto:
            x, y = self.cur
            caixa(d, (x - 10, y - 8, x + 150, y + 26), (255, 255, 255, 230), AZUL, 6)
            notebook_icone(d, x - 2, y - 2, 0.8)
            texto(d, (x + 24, y + 9), self.arrasto, "p", TEXTO, "lm")
        if self.onda is not None:
            clique(d, *self.cur, self.onda)
        cursor(d, *self.cur)
        legenda(d, *self.leg)
        self.quadros.append(im.convert("RGB"))

    def esperar(self, seg):
        for _ in range(max(1, int(seg * FPS))):
            self._quadro()

    def mover(self, alvo, seg=0.7):
        x0, y0 = self.cur
        n = max(2, int(seg * FPS))
        for i in range(1, n + 1):
            t = i / n
            t = 0.5 - math.cos(math.pi * t) / 2   # acelera e desacelera
            self.cur = (int(x0 + (alvo[0] - x0) * t), int(y0 + (alvo[1] - y0) * t))
            self._quadro()

    def clicar(self, alvo=None, duplo=False, **mudancas):
        if alvo:
            self.mover(alvo)
        for _ in range(2 if duplo else 1):
            for i in range(4):
                self.onda = i / 4
                self._quadro()
        self.onda = None
        self.e.update(mudancas)
        self._quadro()

    def digitar(self, chave, s, seg_por_letra=0.09):
        for i in range(1, len(s) + 1):
            self.e[chave] = s[:i]
            for _ in range(max(1, int(seg_por_letra * FPS))):
                self._quadro()

    def mudar(self, **mudancas):
        self.e.update(mudancas)

    def salvar(self, nome):
        os.makedirs(SAIDA, exist_ok=True)
        caminho = os.path.join(SAIDA, nome)
        # paleta unica para o GIF todo: arquivo bem menor e sem cores tremendo entre quadros
        amostra = [self.quadros[int(i * (len(self.quadros) - 1) / 5)] for i in range(6)]
        mosaico = Image.new("RGB", (L, A * len(amostra)))
        for i, q in enumerate(amostra):
            mosaico.paste(q, (0, A * i))
        base = mosaico.quantize(96, method=Image.Quantize.MEDIANCUT)
        quadros = [q.quantize(palette=base, dither=Image.Dither.NONE) for q in self.quadros]
        quadros[0].save(caminho, save_all=True, append_images=quadros[1:], duration=int(1000 / FPS), loop=0, optimize=True)
        print(f"{nome}: {len(quadros)} quadros, {os.path.getsize(caminho) / 1024:.0f} KB")


# ------------------------------------------------------------------------------
# os passos
# ------------------------------------------------------------------------------

def gif_criar_pasta():
    f = Filme(tela_drive, {}, (500, 300))
    f.legenda(1, "No Google Drive: Novo › Nova pasta › ComfyUI Studio › Criar")
    f.esperar(0.6)
    f.clicar((70, 113), menu_novo=True)
    f.mover((110, 120), 0.4)
    f.mudar(menu_hover=0)
    f.esperar(0.3)
    f.clicar(menu_novo=False, menu_hover=None, dialogo_nome="")
    f.mover((420, 230), 0.4)
    f.digitar("dialogo_nome", "ComfyUI Studio")
    f.esperar(0.3)
    f.clicar((532, 300), dialogo_nome=None, pasta_criada=True, destaca_pasta=True)
    f.esperar(1.6)
    f.salvar("1-criar-pasta.gif")


def gif_enviar_arquivo():
    f = Filme(tela_drive, {"pasta_criada": True, "destaca_pasta": True}, (500, 300))
    f.legenda(2, "Abra a pasta e arraste o arquivo comfyui_0800.ipynb para dentro")
    f.esperar(0.4)
    f.clicar((520, 138), duplo=True, dentro=True, janela_arquivo=True)
    f.esperar(0.4)
    f.mover((70, 303), 0.6)
    f.mudar(arrastando=True)
    f.arrasto = "comfyui_0800.ipynb"
    f.mover((470, 260), 1.0)
    f.arrasto = None
    f.mudar(arrastando=False, janela_arquivo=False, upload=True, arquivo=True)
    f.esperar(0.4)
    f.mover((560, 330), 0.5)
    f.esperar(1.6)
    f.salvar("2-enviar-arquivo.gif")


def gif_abrir_colab():
    f = Filme(tela_drive, {"dentro": True, "arquivo": True}, (600, 330))
    f.legenda(3, "Dê dois cliques no arquivo › Abrir com › Google Colaboratory")
    f.esperar(0.4)
    f.clicar((320, 180), duplo=True, arquivo_sel=True, abrir_com=True)
    f.mover((470, 210), 0.5)
    f.mudar(abrir_hover=0)
    f.esperar(0.3)
    f.clicar()
    f.tela, f.e = tela_colab, {}
    f.esperar(1.6)
    f.salvar("3-abrir-colab.gif")


def gif_escolher_t4():
    f = Filme(tela_colab, {}, (500, 300))
    f.legenda(4, "Ambiente de execução › Alterar o tipo › T4 GPU › Salvar")
    f.esperar(0.4)
    x_menu = 58 + sum(ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(m, font=F["p"]) + 16 for m in ["Arquivo", "Editar", "Ver", "Inserir"])
    f.clicar((int(x_menu) + 60, 73), menu_aberto="Ambiente de execução")
    f.mover((int(x_menu) + 120, 216), 0.6)
    f.mudar(menu_hover=3)
    f.esperar(0.3)
    f.clicar(menu_aberto=None, menu_hover=None, dialogo_t4=True)
    f.clicar((267, 242), t4_marcado=True)
    f.esperar(0.4)
    f.clicar((536, 346), dialogo_t4=False, gpu=True)
    f.mover((L - 90, 100), 0.6)
    f.esperar(1.6)
    f.salvar("4-escolher-t4.gif")


def gif_iniciar():
    f = Filme(tela_colab, {"gpu": True}, (600, 260))
    f.legenda(5, "Aperte o ▶ (play). O painel para escolher o pack aparece embaixo")
    f.esperar(0.6)
    f.clicar((47, 131), aviso=True)
    f.clicar((544, 306), aviso=False, rodando=True, painel="escolha")
    f.mover((350, 300), 0.6)
    f.esperar(0.4)
    f.clicar((150, 258), pack_sel=0)
    f.clicar((89, 381))
    f.mudar(painel="instalacao", progresso=0.0)
    for i in range(1, 31):
        f.mudar(progresso=i / 30)
        f._quadro()
    f.esperar(1.8)
    f.salvar("5-iniciar.gif")


def gif_trocar_pack():
    f = Filme(tela_colab, {"gpu": True, "rodando": True, "painel": "instalacao", "progresso": 1.0}, (600, 330))
    f.legenda(6, "Para trocar de pack: ■ parar, ▶ de novo e escolha outro")
    f.esperar(0.6)
    f.clicar((47, 131), rodando=False, painel=None)
    f.esperar(0.4)
    f.clicar((47, 131), rodando=True, painel="escolha", pack_sel=0)
    f.mover((420, 250), 0.6)
    f.clicar((560, 258), pack_sel=2)
    f.esperar(0.4)
    f.clicar((89, 381))
    f.mudar(painel="instalacao", progresso=0.0)
    for i in range(1, 25):
        f.mudar(progresso=i / 24)
        f._quadro()
    f.esperar(1.6)
    f.salvar("6-trocar-pack.gif")


if __name__ == "__main__":
    gif_criar_pasta()
    gif_enviar_arquivo()
    gif_abrir_colab()
    gif_escolher_t4()
    gif_iniciar()
    gif_trocar_pack()
