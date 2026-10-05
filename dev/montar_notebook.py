"""Coloca o codigo de studio_cell.py dentro do notebook. Rode de dentro da pasta dev:  python montar_notebook.py"""
import ast, json
codigo = open("studio_cell.py", encoding="utf-8").read()
ast.parse(codigo)
caminho = "../comfyui_0800.ipynb"
nb = json.load(open(caminho, encoding="utf-8"))
nb["cells"][1]["source"] = codigo.splitlines(keepends=True)
json.dump(nb, open(caminho, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
print("notebook atualizado:", len(codigo.splitlines()), "linhas")
