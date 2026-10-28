"""Barra de status do Claude Code: mostra o seu limite de 5 horas e o semanal, e guarda pro Claudinho.

O Claude Code chama a cada atualização com um JSON no stdin; pra assinantes Pro/Max vem o `rate_limits`
(five_hour / seven_day: used_percentage e resets_at). Grava o último em ~/.claudinho/uso_plano.json e imprime uma
linha curta. Nunca pode travar nem quebrar o Claude Code.
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

DADOS = Path(os.environ.get("CLAUDINHO_DADOS") or Path.home() / ".claudinho")


def janela(nome, j):
    if not j or (j.get("resets_at") and j["resets_at"] < time.time()):
        return None
    resets = datetime.fromtimestamp(j["resets_at"]).strftime("%H:%M" if nome == "5h" else "%d/%m") if j.get(
        "resets_at") else ""
    return f"{nome} {round(j.get('used_percentage') or 0)}%" + (f" (até {resets})" if resets else "")


def main():
    dados = json.loads(sys.stdin.buffer.read().decode("utf-8-sig", "replace") or "{}")
    limites = dados.get("rate_limits") or {}
    if limites.get("five_hour") or limites.get("seven_day"):
        DADOS.mkdir(exist_ok=True)
        temp = DADOS / "uso_plano.json.tmp"
        temp.write_text(json.dumps({"rate_limits": limites, "recebido": time.time(),
                                    "modelo": (dados.get("model") or {}).get("display_name")}), encoding="utf-8")
        os.replace(temp, DADOS / "uso_plano.json")
    partes = [p for p in (janela("5h", limites.get("five_hour")), janela("semana", limites.get("seven_day"))) if p]
    modelo = (dados.get("model") or {}).get("display_name") or ""
    print(" · ".join([modelo, *partes]) if modelo or partes else "")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
