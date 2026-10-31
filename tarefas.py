"""Tarefas agendadas: "às 18h abre o Spotify", "todo dia às 9h me lembra do daily", "toda sexta às 17h toca rock".

Cada tarefa (fica no config, em "tarefas"):
    {"id", "pedido", "lembrete": bool, "hora": "HH:MM", "repetir": "uma|diaria|uteis|semanal",
     "dia": 0-6 (semanal, 0 = segunda), "data": "AAAA-MM-DD" (uma vez), "proxima": epoch | None, "ativa": bool}

Lembrete só avisa (balão e voz, grátis). O resto o Claudinho faz pelo caminho mais barato na hora: comando rápido,
comando seu/aprendido e, só se nada bater, o chat. Ele só roda tarefa enquanto está aberto; perdeu por pouco
(TOLERANCIA), ainda faz; por muito, só avisa que não fez.

    entender(frase) -> {"pedido", "lembrete", "hora", "repetir" ou None, "dia", "data"} ou None
"""
import datetime as dt
import re
import secrets
import unicodedata

REPETIR = {"uma": "uma vez", "diaria": "todo dia", "uteis": "dias úteis", "semanal": "toda semana"}
DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
MAX_TAREFAS = 40
MAX_PEDIDO = 300
TOLERANCIA = 30 * 60      # o PC estava desligado / o Claudinho fechado na hora: até 30 min depois ainda faz


def _hora_valida(hora):
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", str(hora or "").strip())
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        return None
    return f"{int(m.group(1)):02d}:{m.group(2)}"


def _em(dia, hora):
    h, m = map(int, hora.split(":"))
    return dt.datetime.combine(dia, dt.time(h, m))


def proxima(t, depois):
    """Quando a tarefa roda de novo, depois do instante `depois` (epoch). None: não roda mais (uma vez, já passou)."""
    depois_dt = dt.datetime.fromtimestamp(depois)
    if t["repetir"] == "uma":
        try:
            quando = _em(dt.date.fromisoformat(t["data"]), t["hora"])
        except (TypeError, ValueError):
            return None
        return quando.timestamp() if quando > depois_dt else None
    dia = depois_dt.date()
    for _ in range(8):
        quando = _em(dia, t["hora"])
        semana = dia.weekday()
        vale = (t["repetir"] == "diaria" or (t["repetir"] == "uteis" and semana < 5)
                or (t["repetir"] == "semanal" and semana == t.get("dia", 0)))
        if vale and quando > depois_dt:
            return quando.timestamp()
        dia += dt.timedelta(days=1)
    return None


def nova(pedido, hora, repetir="uma", lembrete=False, data=None, dia=None, agora=None):
    """Monta (e confere) uma tarefa. Sem data, "uma vez" é a próxima vez que der aquela hora (hoje ou amanhã);
    "toda semana" sem dia é o dia dessa primeira vez. Devolve (tarefa, None) ou (None, motivo)."""
    agora = agora if agora is not None else dt.datetime.now().timestamp()
    pedido = " ".join(str(pedido or "").split())[:MAX_PEDIDO]
    hora = _hora_valida(hora)
    if not pedido:
        return None, "faltou o que fazer"
    if not hora:
        return None, "hora inválida (use HH:MM)"
    if repetir not in REPETIR:
        return None, "repetição inválida"
    hoje = dt.datetime.fromtimestamp(agora)
    primeira = _em(hoje.date(), hora)
    if primeira <= hoje:
        primeira += dt.timedelta(days=1)
    if data:
        try:
            primeira = _em(dt.date.fromisoformat(str(data)), hora)
        except ValueError:
            return None, "data inválida (use AAAA-MM-DD)"
        if repetir == "uma" and primeira <= hoje:
            return None, "esse horário já passou"
    if repetir == "semanal" and dia is None:
        dia = primeira.weekday()
    t = {"id": secrets.token_hex(4), "pedido": pedido, "lembrete": bool(lembrete), "hora": hora,
         "repetir": repetir, "ativa": True}
    if repetir == "uma":
        t["data"] = primeira.date().isoformat()
    if repetir == "semanal":
        t["dia"] = int(dia) % 7
    t["proxima"] = proxima(t, agora - 1)
    return t, None


def validar_lista(valor, agora=None):
    """O que veio do painel (ou do arquivo editado à mão): só tarefas bem formadas, no máximo MAX_TAREFAS."""
    agora = agora if agora is not None else dt.datetime.now().timestamp()
    saida = []
    for t in valor if isinstance(valor, list) else []:
        if not isinstance(t, dict):
            continue
        dia = t.get("dia")
        nova_t, erro = nova(t.get("pedido"), t.get("hora"), t.get("repetir", "uma"), t.get("lembrete"),
                            t.get("data") if t.get("repetir") == "uma" else None,
                            dia if isinstance(dia, int) and 0 <= dia <= 6 else None, agora)
        if erro and t.get("repetir") == "uma" and _hora_valida(t.get("hora")) and t.get("pedido"):
            nova_t = {**t, "proxima": None, "ativa": False}   # uma vez que já passou: fica na lista, parada
        elif erro:
            continue
        nova_t["id"] = str(t.get("id") or nova_t["id"])[:16]
        nova_t["ativa"] = bool(t.get("ativa", True)) and nova_t["proxima"] is not None
        # a próxima que já estava marcada vale: senão uma tarefa esperando (jogo na frente) "pularia" a vez quando a
        # lista é salva. O painel apaga a "proxima" de quem ele editou, pra ela ser calculada de novo
        if nova_t["ativa"] and isinstance(t.get("proxima"), (int, float)):
            nova_t["proxima"] = t["proxima"]
        saida.append(nova_t)
    return saida[:MAX_TAREFAS]


def vencidas(lista, agora, aberto_em):
    """[(tarefa, "fazer" | "perdida")]: as que chegaram na hora. Perdida = venceu antes do Claudinho abrir e faz
    mais de TOLERANCIA (o PC estava desligado); atraso por jogo ou chat ocupado nunca vira perdida."""
    saida = []
    for t in lista:
        p = t.get("proxima")
        if not t.get("ativa") or not p or p > agora:
            continue
        saida.append((t, "perdida" if p < aberto_em and agora - p > TOLERANCIA else "fazer"))
    return saida


def avancar(t, agora):
    """Rodou (ou perdeu): marca a próxima vez; "uma vez" para."""
    t["proxima"] = proxima(t, agora)
    if t["proxima"] is None:
        t["ativa"] = False
    return t


def descrever(t):
    """ "às 18:00, todo dia: abrir o Spotify" """
    if t["repetir"] == "uma":
        try:
            dia = dt.date.fromisoformat(t["data"])
            hoje = dt.date.today()
            quando = ("hoje" if dia == hoje else "amanhã" if dia == hoje + dt.timedelta(days=1)
                      else dia.strftime("%d/%m"))
        except (KeyError, ValueError):
            quando = "uma vez"
    elif t["repetir"] == "semanal":
        quando = "toda " + DIAS[t.get("dia", 0)] + ("" if t.get("dia", 0) >= 5 else "-feira")
    else:
        quando = REPETIR[t["repetir"]]
    o_que = ("lembrar: " if t.get("lembrete") else "") + t["pedido"]
    return f"{quando} às {t['hora']}: {o_que}"


# ---------- entender a frase sem IA ----------
_DIA_RE = r"(segunda|terca|quarta|quinta|sexta|sabado|domingo)(?:\s*-?\s*feira)?"
_RECORRENCIA = [
    ("diaria", re.compile(r"\b(?:todo\s+dia|todos\s+os\s+dias|diariamente|toda\s+manha|toda\s+noite|"
                          r"toda\s+tarde)\b")),
    ("uteis", re.compile(r"\b(?:(?:todo|em)\s+dias?\s+uteis|nos\s+dias\s+uteis|dias\s+uteis|"
                         r"de\s+segunda\s+a\s+sexta)\b")),
    ("semanal", re.compile(r"\b(?:tod[ao]s?\s+(?:as?\s+|os?\s+)?)" + _DIA_RE + r"s?\b")),
    ("semanal", re.compile(r"\btoda\s+semana\b")),
]
_HORA = re.compile(r"\b(?:as|a|pras|para\s+as|la\s+pelas|pelas)\s+(?P<h>\d{1,2})(?:\s*(?:h|horas?|:)\s*(?P<m>\d{2})?"
                   r"(?:\s*(?:min|minutos?))?)?(?:\s+(?:e\s+(?P<meia>meia)))?"
                   r"(?:\s+(?P<periodo>da\s+manha|da\s+tarde|da\s+noite|da\s+madrugada))?\b"
                   r"|\b(?P<especial>ao\s+meio\s+dia|meio\s+dia|a\s+meia\s+noite|meia\s+noite)\b")
_QUANDO = re.compile(r"\b(?P<qual>hoje|amanha|depois\s+de\s+amanha)(?:\s+(?:de\s+manha|a\s+tarde|a\s+noite))?\b")
_LEMBRETE = re.compile(r"^(?:me\s+)?(?:lembra|lembre|lembrar|avisa|avise|chama)(?:\s*-?\s*me)?\s+(?:de\s+que\s+|de\s+|"
                       r"que\s+|pra\s+|para\s+)?(?P<o_que>.+)$")
_ABERTURA = re.compile(r"^(?:(?:ei|oi|ola|fala|e\s+ai)\s+)?(?:claudinho\s*)?(?:,\s*)?(?:por\s+favor\s+)?")


def _limpo(frase):
    """Minúsculas sem acento, pontuação vira espaço (menos o ':' da hora e o '-')."""
    return " ".join(_espelho(frase)[0].split())


def _espelho(frase):
    """(base, original) do mesmo tamanho, letra por letra: a base sem acento (onde as regras procuram) e o original
    (de onde sai o pedido, com acento e maiúscula). Pontuação vira espaço nas duas, então os espaços coincidem."""
    base, orig = [], []
    for c in str(frase or ""):
        b = (unicodedata.normalize("NFKD", c.lower()) or " ")[0]
        if not re.fullmatch(r"[a-z0-9:-]", b):
            b = c = " "
        base.append(b)
        orig.append(c)
    return "".join(base), "".join(orig)


def _juntar(base, orig):
    """Espaços simples nas duas, sem perder o alinhamento (os espaços estão nas mesmas posições)."""
    return " ".join(base.split()), " ".join(orig.split())


def entender(frase, agora=None):
    """Frase de agendamento ("às 18h abre o Spotify", "me lembra amanhã às 9 de pagar a conta", "todo dia às 8h
    toca lo-fi")? Devolve o que entendeu (repetir None = ele não disse: pergunta com botões) ou None.

    A hora tem que estar no começo ou no fim do pedido (ou ser um "me lembra"): "o que eu fiz às 18h ontem?" não
    é agendamento."""
    agora_dt = dt.datetime.fromtimestamp(agora) if agora is not None else dt.datetime.now()
    texto, orig = _juntar(*_espelho(frase))
    corte = _ABERTURA.match(texto).end()
    texto, orig = texto[corte:], orig[corte:]
    if not texto.strip() or len(texto.split()) > 25:
        return None
    m = _HORA.search(texto)
    if not m:
        return None
    if m.group("especial"):
        h, mi = (0 if "noite" in m.group("especial") else 12), 0
    else:
        h, mi = int(m.group("h")), int(m.group("m") or (30 if m.group("meia") else 0))
        periodo = m.group("periodo") or ""
        if ("tarde" in periodo or "noite" in periodo) and h < 12:
            h += 12
        if h > 23 or mi > 59:
            return None
    partes = [(m.start(), m.end())]
    repetir, dia = None, None
    for qual, padrao in _RECORRENCIA:
        r = padrao.search(texto)
        if r:
            repetir = qual
            if qual == "semanal" and r.groups() and r.group(1):
                dia = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"].index(r.group(1))
            partes.append((r.start(), r.end()))
            break
    data = None
    q = _QUANDO.search(texto)
    if q and not repetir:
        dias = {"hoje": 0, "amanha": 1}.get(q.group("qual"), 2)
        data = (agora_dt.date() + dt.timedelta(days=dias)).isoformat()
        repetir = "uma"
        partes.append((q.start(), q.end()))
    # tira o "quando" da frase: o que sobra é o pedido (com os acentos do original)
    pedacos, fim = [], 0
    for a, b in sorted(partes):
        pedacos.append((texto[fim:a], orig[fim:a]))
        fim = max(fim, b)
    pedacos.append((texto[fim:], orig[fim:]))
    na_ponta = not pedacos[0][0].strip() or not pedacos[-1][0].strip()   # o "quando" abre ou fecha a frase
    base, pedido = _juntar(" ".join(p[0] for p in pedacos), " ".join(p[1] for p in pedacos))
    e = re.match(r"(?:e\s+)?", base).end()
    base, pedido = base[e:], pedido[e:]
    lembrete = _LEMBRETE.match(base)
    if not lembrete and not na_ponta:
        return None
    if lembrete:
        base, pedido = base[lembrete.start("o_que"):], pedido[lembrete.start("o_que"):]
        e = re.match(r"(?:(?:de|que|pra|para)\s+)?", base).end()
        base, pedido = base[e:], pedido[e:]
    f = re.search(r"(?:\s+(?:por\s+favor|pra\s+mim|claudinho))*$", base).start()
    base, pedido = base[:f].strip(), pedido[:f].strip()
    # "toca às 10" sozinho é mais provável ser outra coisa do que um agendamento (lembrete curto vale: "de almoçar")
    if len(base.split()) < (1 if lembrete else 2):
        return None
    return {"pedido": pedido, "lembrete": bool(lembrete), "hora": f"{h:02d}:{mi:02d}", "repetir": repetir,
            "dia": dia, "data": data}


def repeticao_da_resposta(texto):
    """A resposta pra "uma vez ou repete?" falada/digitada: "só hoje", "todo dia", "dias úteis", "toda semana"."""
    t = _limpo(texto)
    if re.search(r"\b(?:semanal|toda\s+semana|uma\s+vez\s+por\s+semana)\b", t):
        return "semanal"
    if re.search(r"\b(?:uma\s+vez|so\s+hoje|so\s+essa|so\s+amanha|nao\s+repete|uma\s+so)\b", t):
        return "uma"
    for qual, padrao in _RECORRENCIA:
        if padrao.search(t):
            return qual
    if re.search(r"\b(?:diario|diaria|sempre)\b", t):
        return "diaria"
    return None
