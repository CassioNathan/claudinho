"""Consumo: o do seu plano do Claude (limite de 5 horas e semanal) e o do próprio Claudinho.

    plano      a barra de status do Claude Code (hook/claudinho_status.py) grava o rate_limits que ele recebe em
               ~/.claudinho/uso_plano.json; só atualiza enquanto você usa o Claude Code
    claudinho  cada chamada do Claudinho (chat, piadas, Júnior, revisão…) soma o custo e os tokens que o Claude
               devolve, por dia e no total, em ~/.claudinho/consumo.json

Os arquivos podem ter sido editados à mão ou gravados pela metade: tudo aqui aceita formato estranho sem cair (o
consumo é só informação; nunca pode derrubar o chat).
"""
import json
import os
import sys
import threading
import time
from datetime import date, datetime

import sistema

PLANO = sistema.DADOS / "uso_plano.json"
ARQUIVO = sistema.DADOS / "consumo.json"
_trava = threading.Lock()

NUMEROS = ("custo", "entrada", "saida", "chamadas")


def _numero(valor, tipo=float):
    try:
        return tipo(valor)
    except (TypeError, ValueError):
        return tipo(0)


def _parte(dados, **extra):
    """Uma parte (hoje/total) com todos os campos, números de verdade e o por_tarefa como dict."""
    dados = dados if isinstance(dados, dict) else {}
    parte = {"custo": _numero(dados.get("custo")), "entrada": _numero(dados.get("entrada"), int),
             "saida": _numero(dados.get("saida"), int), "chamadas": _numero(dados.get("chamadas"), int)}
    tarefas = dados.get("por_tarefa")
    parte["por_tarefa"] = {str(k): _numero(v) for k, v in tarefas.items()} if isinstance(tarefas, dict) else {}
    for chave, padrao in extra.items():
        parte[chave] = dados.get(chave) if isinstance(dados.get(chave), str) else padrao
    return parte


def _ler():
    try:
        dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        dados = {}
    if not isinstance(dados, dict):
        dados = {}
    hoje = date.today().isoformat()
    total = _parte(dados.get("total"), desde=hoje)
    dia = (dados.get("hoje") or {}).get("dia") if isinstance(dados.get("hoje"), dict) else None
    parte_hoje = _parte(dados.get("hoje"), dia=hoje) if dia == hoje else _parte({}, dia=hoje)   # virou o dia
    return {"total": total, "hoje": parte_hoje}


def _gravar(dados):
    """Grava num .tmp e troca de uma vez: um processo lendo nunca pega o arquivo pela metade."""
    sistema.DADOS.mkdir(exist_ok=True)
    tmp = ARQUIVO.with_name(f"{ARQUIVO.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, ARQUIVO)


def registrar(tarefa, custo=0.0, entrada=0, saida=0):
    """Soma uma chamada do Claudinho. `custo` em US$ (o que o Claude Code calcula; no plano é só referência).
    Nunca levanta erro: falhar aqui não pode derrubar a chamada que já deu certo."""
    custo, entrada, saida = _numero(custo), _numero(entrada, int), _numero(saida, int)
    if not (custo or entrada or saida):
        return
    try:
        with _trava:
            dados = _ler()
            for parte in (dados["hoje"], dados["total"]):
                parte["custo"] += custo
                parte["entrada"] += entrada
                parte["saida"] += saida
                parte["chamadas"] += 1
                parte["por_tarefa"][str(tarefa)] = parte["por_tarefa"].get(str(tarefa), 0.0) + custo
            _gravar(dados)
    except Exception as e:
        print("não consegui registrar o consumo:", e, file=sys.stderr)


def _campo(uso, chave):
    """Um número do `usage` do Claude, venha ele como dict (JSON do Claude Code) ou objeto (SDK da API)."""
    valor = uso.get(chave) if isinstance(uso, dict) else getattr(uso, chave, 0)
    return _numero(valor, int)


def tokens_de(uso):
    """(entrada, saída) de um `usage` do Claude: a entrada conta o cache lido e o criado."""
    uso = uso or {}
    entrada = sum(_campo(uso, k) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    return entrada, _campo(uso, "output_tokens")


def preco(modelo):
    """US$ por milhão de tokens (entrada, saída), da tabela de modelos do motores.py, pra estimar o que a API não
    devolve pronto. Vale o começo do id: "claude-haiku-5-5-20261001" (id com data) usa o preço do "claude-haiku-5-5";
    modelo desconhecido conta como Sonnet."""
    import motores   # aqui dentro: o motores importa este módulo
    modelo = str(modelo or "")
    return next((m["preco"] for m in motores.MODELOS.values() if modelo.startswith(m["id"])),
                motores.MODELOS["sonnet"]["preco"])


def custo_api(modelo, uso):
    """Estimativa em US$ de uma chamada da API (cache lido sai a ~10%, criado a ~125% da entrada)."""
    preco_in, preco_out = preco(modelo)
    uso = uso or {}
    entrada = (_campo(uso, "input_tokens") + 1.25 * _campo(uso, "cache_creation_input_tokens")
               + 0.1 * _campo(uso, "cache_read_input_tokens"))
    return (entrada * preco_in + _campo(uso, "output_tokens") * preco_out) / 1_000_000


def do_claudinho():
    with _trava:
        return _ler()


def do_plano():
    """O último rate_limits que a barra de status viu (ou None), com há quanto tempo veio (None se não se sabe)."""
    try:
        dados = json.loads(PLANO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(dados, dict):
        return None
    recebido = _numero(dados.get("recebido"))
    dados["ha_minutos"] = int((time.time() - recebido) / 60) if recebido else None
    return dados


def janela(j):
    """(porcentagem usada, quando reseta como datetime ou None, já resetou?) de uma janela do rate_limits.
    É a conta que a barra de status, o painel e o chat mostram, cada um do seu jeito."""
    if not isinstance(j, dict) or not j:   # janela sem dado nenhum: não mostra "0% usado"
        return None
    resets = _numero(j.get("resets_at")) or None
    try:
        quando = datetime.fromtimestamp(resets) if resets else None
    except (OverflowError, OSError, ValueError):
        quando, resets = None, None
    return round(_numero(j.get("used_percentage"))), quando, bool(resets and resets < time.time())


def janelas_do_plano(plano=None):
    """As janelas que ainda valem, prontas pro painel: {"five_hour": {"pct": 40, "reseta": timestamp ou None}, …}."""
    plano = do_plano() if plano is None else plano
    limites = plano.get("rate_limits") if isinstance(plano, dict) else None
    saida = {}
    for chave in ("five_hour", "seven_day"):
        dados = janela((limites or {}).get(chave)) if isinstance(limites, dict) else None
        if dados and not dados[2]:
            saida[chave] = {"pct": dados[0], "reseta": dados[1].timestamp() if dados[1] else None}
    return saida


def _janela(nome, j):
    dados = janela(j)
    if not dados:
        return None
    pct, quando, resetou = dados
    data = quando.strftime("%d/%m %H:%M") if quando else "?"
    if resetou:
        return f"{nome}: já resetou ({data})"
    return f"{nome}: {pct}% usado, reseta {data}"


def texto():
    """Tudo em poucas linhas, pro chat responder "quanto eu já gastei?"."""
    linhas = []
    plano = do_plano()
    r = plano.get("rate_limits") if plano else None
    if isinstance(r, dict) and r:
        linhas += [x for x in (_janela("Limite de 5 horas", r.get("five_hour")),
                               _janela("Limite semanal", r.get("seven_day"))) if x]
        visto = f"há {plano['ha_minutos']} min" if plano["ha_minutos"] is not None else "não sei quando"
        linhas.append(f"(visto pela barra de status do Claude Code {visto}; só atualiza enquanto ele usa o Claude Code)")
    else:
        linhas.append("Plano do Claude: ainda sem dados (a barra de status do Claudinho precisa estar ligada no painel "
                      "→ Sistema, e o Claude Code precisa ter sido usado depois disso; só existe pra Pro/Max)")
    c = do_claudinho()
    for rotulo, parte in (("Claudinho hoje", c["hoje"]), (f"Claudinho desde {c['total']['desde']}", c["total"])):
        tokens = f"{parte['entrada'] + parte['saida']:,}".replace(",", ".")
        linhas.append(f"{rotulo}: {parte['chamadas']} chamadas, {tokens} tokens, "
                      f"~US$ {parte['custo']:.2f} (no plano é referência, não cobrança)")
    return "\n".join(linhas)
