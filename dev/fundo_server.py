"""Servidor do removedor de fundo: rembg (modelo ISNet), na CPU.

Roda num ambiente Python proprio porque o rembg exige versoes de Pillow e numpy mais novas que as do Colab;
instalar no ambiente principal trocava essas bibliotecas com a sessao em andamento e quebrava outras partes.

    POST /recortar  corpo = imagem (PNG, JPG, WebP...) -> image/png com fundo transparente
    GET  /estado    {"online", "modelo"}
"""
import argparse
import io
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PIL import Image
from rembg import new_session, remove

ap = argparse.ArgumentParser()
ap.add_argument("--porta", type=int, default=8190)
ap.add_argument("--modelo", default="isnet-general-use")
args = ap.parse_args()

sessao = new_session(args.modelo)   # na primeira vez baixa o modelo (170 MB); a porta so abre depois disso
trava = threading.Lock()


class H(BaseHTTPRequestHandler):
    def _enviar(self, codigo, corpo, tipo="application/json"):
        if isinstance(corpo, dict):
            corpo = json.dumps(corpo).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        if self.path != "/estado":
            return self._enviar(404, {"erro": "nao existe"})
        self._enviar(200, {"online": True, "modelo": args.modelo})

    def do_POST(self):
        if self.path != "/recortar":
            return self._enviar(404, {"erro": "nao existe"})
        dados = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        try:
            img = Image.open(io.BytesIO(dados)).convert("RGB")
        except Exception:
            return self._enviar(400, {"erro": "não consegui ler a imagem (envie PNG, JPG ou WebP)"})
        try:
            with trava:
                recorte = remove(img, session=sessao)
            saida = io.BytesIO()
            recorte.save(saida, "PNG")
        except Exception as e:   # devolve o erro em vez de derrubar o servidor
            return self._enviar(500, {"erro": f"{type(e).__name__}: {e}"})
        self._enviar(200, saida.getvalue(), "image/png")

    def log_message(self, fmt, *a):
        print(fmt % a, flush=True)


if __name__ == "__main__":
    print(f"removedor de fundo ({args.modelo}) em http://127.0.0.1:{args.porta}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.porta), H).serve_forever()
