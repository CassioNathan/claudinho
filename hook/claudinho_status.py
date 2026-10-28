"""Barra de status do Claude Code: mostra o seu limite de 5 horas e o semanal, e guarda pro Claudinho.

O Claude Code chama a cada atualização com um JSON no stdin; pra assinantes Pro/Max vem o `rate_limits`
(five_hour / seven_day: used_percentage e resets_at). Grava o último em ~/.claudinho/uso_plano.json e imprime uma
linha curta. Nunca pode travar nem quebrar o Claude Code: um erro vai pra ~/.claudinho/status_erro.txt.
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import consumo   # a conta da janela é a mesma do painel e do chat
except ImportError:  # rodando o arquivo direto, fora do cli.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import consumo

DADOS = Path(os.environ.get("CLAUDINHO_DADOS") or Path.home() / ".claudinho")


def janela(nome, j):
    """"5h 40% (até 18:30)"; None se não tem dado ou se a janela já resetou."""
    dados = consumo.janela(j)
    if not dados or dados[2]:
        return None
    pct, quando, _ = dados
    quando = quando.strftime("%H:%M" if nome == "5h" else "%d/%m") if quando else ""
    return f"{nome} {pct}%" + (f" (até {quando})" if quando else "")


def _main():
    dados = json.loads(sys.stdin.buffer.read().decode("utf-8-sig", "replace") or "{}")
    dados = dados if isinstance(dados, dict) else {}
    limites = dados.get("rate_limits") if isinstance(dados.get("rate_limits"), dict) else {}
    modelo = (dados.get("model") or {}).get("display_name") if isinstance(dados.get("model"), dict) else None
    if limites.get("five_hour") or limites.get("seven_day"):
        DADOS.mkdir(exist_ok=True)
        temp = DADOS / "uso_plano.json.tmp"
        temp.write_text(json.dumps({"rate_limits": limites, "recebido": time.time(), "modelo": modelo}),
                        encoding="utf-8")
        os.replace(temp, DADOS / "uso_plano.json")
    partes = [p for p in (janela("5h", limites.get("five_hour")), janela("semana", limites.get("seven_day"))) if p]
    print(" · ".join([modelo or "", *partes]).strip(" ·") if modelo or partes else "")


def main():
    """Chamado pelo Claude Code (direto ou pelo `claudinho-cli status`): nunca levanta erro."""
    try:
        _main()
    except Exception as e:
        try:
            DADOS.mkdir(exist_ok=True)
            (DADOS / "status_erro.txt").write_text(f"{datetime.now():%d/%m %H:%M} {type(e).__name__}: {e}\n",
                                                   encoding="utf-8")
        except OSError:
            pass


if __name__ == "__main__":
    main()
    sys.exit(0)
