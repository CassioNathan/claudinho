"""Consumo: o do seu plano do Claude (limite de 5 horas e semanal) e o do próprio Claudinho.

    plano      a barra de status do Claude Code (hook/claudinho_status.py) grava o rate_limits que ele recebe em
               ~/.claudinho/uso_plano.json; só atualiza enquanto você usa o Claude Code
    claudinho  cada chamada do Claudinho (chat, piadas, Júnior, revisão…) soma o custo e os tokens que o Claude
               devolve, por dia e no total, em ~/.claudinho/consumo.json
"""
import json
import threading
import time
from datetime import date, datetime

import sistema

PLANO = sistema.DADOS / "uso_plano.json"
ARQUIVO = sistema.DADOS / "consumo.json"
_trava = threading.Lock()

# US$ por milhão de tokens (entrada, saída), pra estimar o que a API não devolve pronto
PRECOS = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.00, 10.00), "claude-opus-5-5": (4.00, 20.00)}


def _vazio():
    return {"custo": 0.0, "entrada": 0, "saida": 0, "chamadas": 0, "por_tarefa": {}}


def _ler():
    try:
        dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        dados = {}
    dados.setdefault("total", dict(_vazio(), desde=date.today().isoformat()))
    if (dados.get("hoje") or {}).get("dia") != date.today().isoformat():  # virou o dia: o "hoje" recomeça
        dados["hoje"] = dict(_vazio(), dia=date.today().isoformat())
    return dados


def registrar(tarefa, custo=0.0, entrada=0, saida=0):
    """Soma uma chamada do Claudinho. `custo` em US$ (o que o Claude Code calcula; no plano é só referência)."""
    if not (custo or entrada or saida):
        return
    with _trava:
        dados = _ler()
        for parte in (dados["hoje"], dados["total"]):
            parte["custo"] += float(custo or 0)
            parte["entrada"] += int(entrada or 0)
            parte["saida"] += int(saida or 0)
            parte["chamadas"] += 1
            parte["por_tarefa"][tarefa] = parte["por_tarefa"].get(tarefa, 0.0) + float(custo or 0)
        sistema.DADOS.mkdir(exist_ok=True)
        ARQUIVO.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")


def tokens_de(uso):
    """(entrada, saída) de um `usage` do Claude: a entrada conta o cache lido e o criado."""
    uso = uso or {}
    pega = uso.get if isinstance(uso, dict) else (lambda k, d=0: getattr(uso, k, d) or 0)
    entrada = sum(int(pega(k, 0) or 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    return entrada, int(pega("output_tokens", 0) or 0)


def custo_api(modelo, uso):
    """Estimativa em US$ de uma chamada da API (cache lido sai a ~10%, criado a ~125% da entrada)."""
    preco_in, preco_out = PRECOS.get(modelo, PRECOS["claude-sonnet-5-5"])
    pega = (lambda k: getattr(uso, k, 0) or 0)
    entrada = pega("input_tokens") + 1.25 * pega("cache_creation_input_tokens") + 0.1 * pega("cache_read_input_tokens")
    return (entrada * preco_in + pega("output_tokens") * preco_out) / 1_000_000


def do_claudinho():
    with _trava:
        return _ler()


def do_plano():
    """O último rate_limits que a barra de status viu (ou None), com há quanto tempo veio."""
    try:
        dados = json.loads(PLANO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    dados["ha_minutos"] = int((time.time() - dados.get("recebido", 0)) / 60)
    return dados


def _janela(nome, j):
    if not j:
        return None
    resets = j.get("resets_at")
    quando = datetime.fromtimestamp(resets).strftime("%d/%m %H:%M") if resets else "?"
    if resets and resets < time.time():
        return f"{nome}: já resetou ({quando})"
    return f"{nome}: {round(j.get('used_percentage') or 0)}% usado, reseta {quando}"


def texto():
    """Tudo em poucas linhas, pro chat responder "quanto eu já gastei?"."""
    linhas = []
    plano = do_plano()
    if plano and plano.get("rate_limits"):
        r = plano["rate_limits"]
        linhas += [x for x in (_janela("Limite de 5 horas", r.get("five_hour")),
                               _janela("Limite semanal", r.get("seven_day"))) if x]
        linhas.append(f"(visto pela barra de status do Claude Code há {plano['ha_minutos']} min; só atualiza enquanto "
                      "ele usa o Claude Code)")
    else:
        linhas.append("Plano do Claude: ainda sem dados (a barra de status do Claudinho precisa estar ligada no painel "
                      "→ Sistema, e o Claude Code precisa ter sido usado depois disso; só existe pra Pro/Max)")
    c = do_claudinho()
    for rotulo, parte in (("Claudinho hoje", c["hoje"]), (f"Claudinho desde {c['total'].get('desde')}", c["total"])):
        tokens = f"{parte['entrada'] + parte['saida']:,}".replace(",", ".")
        linhas.append(f"{rotulo}: {parte['chamadas']} chamadas, {tokens} tokens, "
                      f"~US$ {parte['custo']:.2f} (no plano é referência, não cobrança)")
    return "\n".join(linhas)
