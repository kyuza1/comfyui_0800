"""Gera o preview do painel online (com voz e IA local) e durante a instalacao da IA de chat."""
import sys
import time
import types

m = types.ModuleType("IPython")
d = types.ModuleType("IPython.display")
d.HTML = lambda x: x
d.display = lambda *a, **k: None
d.clear_output = lambda *a, **k: None
sys.modules["IPython"] = m
sys.modules["IPython.display"] = d

src = open("cell_v2.py", encoding="utf-8").read().split("# ------------------------------------------------------------------------------\n# EXECUCAO")[0]
assert "VOZ = False #@param" in src
src = src.replace("VOZ = False #@param", "VOZ = True #@param")
g = {}
exec(src, g)
est, ui = g["estado"], g["ui"]
print("etapas:", list(est))
g["T0"] = time.time() - 540
for k in est:
    est[k].update(status="ok", dt=5, t0=0)
est["gpu"]["info"] = "Tesla T4, 15360 MiB"
ui.update(link="https://mass-dealers-expired-borders.trycloudflare.com", link_api="https://quiet-river-sample-words.trycloudflare.com",
          link_colab="https://8188-gpu-t4-s-kkb-usw1b1-3spoi3vihpqii-b.us-west1-1.prod.colab.dev", online=time.time() - 185, t_fim=time.time())
ui["api_log"] += ["[9:12] chat gerar_imagem · \"a yellow sun on a deep blue background\"", "[10:14] imagem pronta em 61s · api_00003_.png"]
g["ultimas_linhas"] = lambda n=12, caminho=None: "[INFO] Starting server\n[INFO] To see the GUI go to: http://0.0.0.0:8188\nloaded completely 9.5 GB\n100%|██████████| 9/9 [00:14<00:00,  1.6s/it]"
real = g["metricas"]()
print("medido de verdade nesta maquina:", real)
g["metricas"] = lambda: [("RAM 7.4/12.7 GB", False), ("GPU 11.8/15 GB · 96% · 61°C", False), ("disco livre 41 GB", False)]
online = g["render"]()

g2 = {}
exec(src, g2)
est = g2["estado"]
g2["T0"] = time.time() - 300
for k in list(est)[:list(est).index("chat_modelo")]:
    est[k].update(status="ok", dt=5, t0=0)
est["chat_modelo"].update(status="rodando", t0=time.time() - 12, pct=58.0, info="pulling a3de86cd1c13:  58% 1.5 GB/2.6 GB  95 MB/s")
g2["metricas"] = g["metricas"]
instalando = g2["render"]()
est["chat_inst"].update(status="aviso", info="não instalou; o chat fica desligado")
open("preview_online.html", "w", encoding="utf-8").write("<meta charset='utf-8'><body style='margin:20px;background:#fff'>" + online)
open("preview_instalando.html", "w", encoding="utf-8").write("<meta charset='utf-8'><body style='margin:20px;background:#fff'>" + instalando)
print("copiar presente:", online.count("onmousedown="), "| tamanho html:", len(online))
