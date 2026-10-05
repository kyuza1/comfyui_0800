"""Servidor de voz: Chatterbox pt-BR (Resemble AI, MIT) clonando uma voz de referencia de ~10 s.

Roda no ambiente proprio do Chatterbox (torch 2.6), separado do ComfyUI. Uma fala por vez (a GPU e uma so).

    POST /falar    {"texto", "referencia": caminho do audio (opcional), "lingua", "exaggeration", "cfg_weight"} -> audio/wav
    POST /liberar  tira o modelo da GPU (para o ComfyUI usar a memoria)
    GET  /estado   {"online", "carregado", "vram_gb"}
"""
import argparse
import gc
import io
import json
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import soundfile as sf
import torch

ap = argparse.ArgumentParser()
ap.add_argument("--porta", type=int, default=8189)
ap.add_argument("--modelo", required=True, help="pasta com t3, s3gen.pt, ve.pt, tokenizer e conds.pt")
ap.add_argument("--t3", default="t3_pt_br.safetensors")
args = ap.parse_args()

_trava = threading.Lock()
_modelo = None
_padrao = None   # voz embutida do modelo (conds.pt), usada quando nao vem referencia
_conds = {}      # (referencia, mtime) -> condicionamento ja calculado


def modelo():
    global _modelo, _padrao
    if _modelo is None:
        from chatterbox.models.s3gen import S3Gen
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        if not getattr(S3Gen, "_carga_tolerante", False):
            orig = S3Gen.load_state_dict

            def carrega(self, sd, strict=True, **kw):
                # o s3gen v3 vem sem 2 buffers que o proprio Chatterbox marca como ignoraveis (calculados no __init__)
                r = orig(self, sd, strict=False, **kw)
                assert set(r.missing_keys) <= {"tokenizer._mel_filters", "tokenizer.window"} and not r.unexpected_keys, r
                return r
            S3Gen.load_state_dict = carrega
            S3Gen._carga_tolerante = True
        _modelo = ChatterboxMultilingualTTS.from_local(args.modelo, "cuda" if torch.cuda.is_available() else "cpu",
                                                       t3_model=args.t3)
        _padrao = _modelo.conds
    return _modelo


def pedacos(texto, limite=280):
    """Quebra o texto em trechos curtos (o modelo perde qualidade em falas longas), respeitando as frases."""
    frases = [f for f in re.split(r"(?<=[.!?…;:])\s+", texto.strip()) if f]
    partes, atual = [], ""
    for frase in frases:
        while len(frase) > limite:   # frase gigante: corta na ultima virgula ou espaco antes do limite
            corte = max(frase.rfind(", ", 0, limite), frase.rfind(" ", 0, limite))
            corte = corte if corte > 0 else limite
            partes.append((atual + " " + frase[:corte + 1]).strip() if atual else frase[:corte + 1].strip())
            atual, frase = "", frase[corte + 1:]
        if atual and len(atual) + len(frase) + 1 > limite:
            partes.append(atual)
            atual = frase
        else:
            atual = (atual + " " + frase).strip()
    if atual:
        partes.append(atual)
    return partes


def falar(b):
    with _trava:
        m = modelo()
        exag = float(b.get("exaggeration", 0.5))
        ref = b.get("referencia")
        if ref:
            chave = (ref, os.path.getmtime(ref))
            if chave not in _conds:
                m.prepare_conditionals(ref, exaggeration=exag)
                _conds[chave] = m.conds
            m.conds = _conds[chave]
        else:
            m.conds = _padrao
        pausa = torch.zeros(1, int(m.sr * 0.18))
        trechos = []
        for parte in pedacos(b["texto"]):
            wav = m.generate(parte, language_id=b.get("lingua", "pt"), exaggeration=exag,
                             cfg_weight=float(b.get("cfg_weight", 0.5)), temperature=float(b.get("temperature", 0.8)))
            trechos += [wav.cpu(), pausa]
        audio = torch.cat(trechos[:-1], dim=-1).squeeze(0).numpy()
        buf = io.BytesIO()
        sf.write(buf, audio, m.sr, format="WAV", subtype="PCM_16")
        return buf.getvalue()


def liberar():
    global _modelo, _padrao
    with _trava:
        _modelo = _padrao = None
        _conds.clear()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


class H(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path != "/estado":
            return self._json(404, {"erro": "nao existe"})
        vram = torch.cuda.memory_allocated() / 2**30 if torch.cuda.is_available() else 0
        self._json(200, {"online": True, "carregado": _modelo is not None, "vram_gb": round(vram, 2), "modelo": args.t3})

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length") or 0)
        corpo = self.rfile.read(tamanho) if tamanho else b"{}"
        if self.path == "/liberar":
            liberar()
            return self._json(200, {"ok": True})
        if self.path != "/falar":
            return self._json(404, {"erro": "nao existe"})
        try:
            b = json.loads(corpo)
            if not (b.get("texto") or "").strip():
                return self._json(400, {"erro": "texto vazio"})
            t = time.time()
            data = falar(b)
        except Exception as e:   # devolve o erro em vez de derrubar o servidor
            return self._json(500, {"erro": f"{type(e).__name__}: {e}"})
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Segundos", f"{time.time() - t:.2f}")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *a):
        print(time.strftime("%H:%M:%S"), fmt % a, flush=True)


if __name__ == "__main__":
    print(f"voz (Chatterbox {args.t3}) em http://127.0.0.1:{args.porta}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.porta), H).serve_forever()
