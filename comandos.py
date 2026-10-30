"""Comandos rápidos da voz: o que tem resposta certa não passa pela IA.

"Pausa", "próxima", "toca Legião Urbana", "abre o Spotify", "que horas são", "timer de 5 minutos", "aumenta o
volume": a frase inteira tem que ser só o comando (curta e no formato). Qualquer coisa a mais ("abre o projeto e me
diz o que tem") vai pro chat, que entende melhor. É o truque da Alexa: comando fechado é instantâneo e não erra por
interpretar demais.

    entender(texto) -> (acao, argumento) ou None
"""
import re
import unicodedata

MAX_PALAVRAS = 9          # comando de voz é curto: frase maior que isso é conversa, vai pro chat
NUMEROS = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7,
           "oito": 8, "nove": 9, "dez": 10, "quinze": 15, "vinte": 20, "trinta": 30, "quarenta": 40,
           "quarenta e cinco": 45, "meia": 30}
UNIDADES = {"segundo": 1, "segundos": 1, "minuto": 60, "minutos": 60, "hora": 3600, "horas": 3600}
MAX_TIMER_S = 12 * 3600

# "ei, pausa", "tá beleza, rola mais", "na verdade, pausa o vídeo" ainda são comando: tira esse começo e fim
_EDU = r"(?:(?:por favor|claudinho|ai|ei|oi|ta|beleza|ok|certo|agora|na verdade|entao|tipo|ah|cara)\s+)*"
_FIM = r"(?:\s+(?:por favor|ai|pra mim|claudinho|beleza|ta|ok))*"
_VIDEO = r"(?:o\s+|esse\s+|este\s+)?(?:video|youtube)(?:\s+que\s+(?:ta|esta)\s+(?:tocando|rodando|rolando|passando))?"
_MUSICA = r"(?:\s+(?:a|essa|esta)?\s*(?:musica|som|faixa))?"

FIXOS = [
    ("video_pausar", rf"(?:pausa|pausar|pause|para|parar|pare)\s+{_VIDEO}"),
    ("video_tocar", rf"(?:da|de|dar|aperta)\s+(?:o\s+|um\s+)?play(?:\s+(?:no|nesse)\s+(?:video|youtube))?|"
                    rf"(?:continua|continuar|despausa|volta|solta|roda)\s+{_VIDEO}"),
    ("rolar_cima", r"(?:(?:rola|rolar|sobe|subir|volta)(?:\s+(?:a|o))?(?:\s+(?:tela|pagina))?\s+(?:pra|para)\s+cima|"
                   r"(?:sobe|subir)(?:\s+a)?\s+(?:tela|pagina))(?:\s+(?:um\s+)?pouco)?(?:\s+mais)?"),
    ("rolar_baixo", r"(?:rola|rolar|desce|descer)(?:\s+(?:a|o|um|pouco|mais|tela|pagina|pra|para|baixo))*"),
    ("pausar", rf"(?:pausa|pausar|pause|para|parar|pare)(?:\s+(?:a|o))?{_MUSICA}"),
    ("tocar", r"(?:continua|continuar|despausa|play|volta a tocar|solta o som|pode tocar)" + _MUSICA),
    ("proxima", rf"(?:proxima|pula|pular|passa|passar|avanca)(?:\s+(?:a|essa|pra proxima))?{_MUSICA}"),
    ("anterior", r"(?:musica anterior|volta a musica|volta uma musica|a anterior|anterior)"),
    ("horas", r"(?:que horas sao|que hora e|que horas e|me diz as horas|horas)"),
    ("volume_mais", r"(?:aumenta|aumentar|sobe|subir)(?:\s+(?:o|um pouco o))?\s+(?:volume|som)(?:\s+um pouco)?"),
    ("volume_menos", r"(?:abaixa|abaixar|diminui|diminuir|baixa|baixar)(?:\s+(?:o|um pouco o))?\s+(?:volume|som)(?:\s+um pouco)?"),
    ("mudo", r"(?:muta|mutar|silencio|tira o som|desliga o som|mudo)"),
]
# "toca X" / "coloca X pra tocar": só música (vídeo do YouTube e o resto vão pro chat)
TOCAR = re.compile(r"(?:toca|tocar|toque|coloca|colocar|bota|botar|poe)\s+(?:a\s+musica\s+|uma\s+musica\s+d[aeo]\s+|"
                   r"musica\s+d[aeo]\s+|um\s+som\s+d[aeo]\s+)?(?P<termo>.+?)(?:\s+pra tocar)?")
ABRIR = re.compile(r"(?:abre|abrir|abra|abri)\s+(?:o\s+|a\s+|meu\s+|minha\s+)?(?P<termo>.+)")
TIMER = re.compile(r"(?:(?:poe|coloca|bota|faz|marca|liga)\s+)?(?:um\s+)?(?:timer|temporizador|cronometro|alarme)\s+"
                   r"(?:de|pra|para)\s+(?P<tempo>.+)")
LEMBRAR = re.compile(r"(?:me\s+)?(?:avisa|lembra|lembre|chama)(?:\s+me)?\s+(?:em|daqui a|daqui)\s+(?P<tempo>.+?)"
                     r"(?:\s+(?:de|que|pra|para)\s+(?P<lembrete>.+))?")
# vídeo: "avança 30 segundos", "volta dez segundos"
PULAR_VIDEO = re.compile(r"(?P<dir>avanca|adianta|pula|volta|retrocede|voltar|avancar)\s+(?:o\s+video\s+)?(?:uns\s+)?"
                         r"(?P<n>\d+|[a-z]+)\s+segundos?")
# abas do navegador: "vai pra aba do YouTube", "volta pro YouTube", "fecha a aba da Strandberg", "fecha essa aba"
IR_ABA = re.compile(r"(?:vai|volta|muda|troca|passa|abre)\s+(?:pra|para|pro|na)\s+(?:a\s+|o\s+)?"
                    r"(?:(?:aba|guia)\s+(?:do\s+|da\s+|de\s+)?)?(?P<termo>.+)")
FECHAR_ABA = re.compile(r"(?:fecha|fechar|feche)\s+(?:a\s+|essa\s+|esta\s+)?(?:aba|guia)(?:\s+(?:do|da|de)\s+(?P<termo>.+))?")
# o que não é nome de programa nem de música: frase com isso é pedido composto, fica pro chat
EMENDAS = {"e", "depois", "entao", "pra", "para", "porque", "que", "se", "quando", "no youtube", "video"}


def normalizar(texto):
    """Minúsculas, sem acento nem pontuação, espaços simples."""
    texto = unicodedata.normalize("NFKD", str(texto or "").lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", texto).split())


def segundos(tempo):
    """"5 minutos", "cinco minutos", "1 hora e meia", "30 segundos" → segundos (ou None)."""
    tempo = normalizar(tempo)
    if re.fullmatch(r"(?:uma\s+)?hora\s+e\s+meia|1\s+hora\s+e\s+meia", tempo):
        return 5400
    if re.fullmatch(r"meia\s+hora", tempo):
        return 1800
    total = 0
    for numero, unidade in re.findall(r"(\d+|[a-z]+(?:\s+e\s+cinco)?)\s+(segundos?|minutos?|horas?)", tempo):
        n = int(numero) if numero.isdigit() else NUMEROS.get(numero)
        if n is None:
            return None
        total += n * UNIDADES[unidade]
    return total if 0 < total <= MAX_TIMER_S else None


def _composto(termo):
    palavras = termo.split()
    return any(p in EMENDAS for p in palavras) or any(e in termo for e in EMENDAS if " " in e)


def entender(texto):
    """(acao, argumento) se a frase for só um comando rápido; None se for conversa (vai pro chat)."""
    frase = normalizar(texto)
    if not frase or len(frase.split()) > MAX_PALAVRAS:
        return None
    frase = re.sub(rf"^{_EDU}", "", frase)
    frase = re.sub(rf"{_FIM}$", "", frase).strip()
    for acao, padrao in FIXOS:
        if re.fullmatch(padrao, frase):
            return acao, None
    m = PULAR_VIDEO.fullmatch(frase)
    if m:
        n = int(m.group("n")) if m.group("n").isdigit() else NUMEROS.get(m.group("n"))
        if n and n <= 600:
            return ("video_voltar" if m.group("dir").startswith(("volta", "retro")) else "video_avancar"), n
    m = FECHAR_ABA.fullmatch(frase)
    if m:
        return "fechar_aba", (m.group("termo") or "").strip()
    m = IR_ABA.fullmatch(frase)
    if m and len(m.group("termo").split()) <= 4 and not _composto(m.group("termo")):
        return "ir_aba", m.group("termo")
    m = TIMER.fullmatch(frase) or LEMBRAR.fullmatch(frase)
    if m:
        s = segundos(m.group("tempo"))
        if s:
            lembrete = (m.groupdict().get("lembrete") or "").strip()
            return "timer", (s, lembrete)
        return None
    m = TOCAR.fullmatch(frase)
    if m and not _composto(m.group("termo")):
        return "musica", m.group("termo")
    m = ABRIR.fullmatch(frase)
    if m and not _composto(m.group("termo")):
        return "abrir", m.group("termo")
    return None


def falar_tempo(s):
    """300 → "5 minutos"; 5400 → "1 hora e 30 minutos"."""
    h, resto = divmod(int(s), 3600)
    m, seg = divmod(resto, 60)
    partes = [f"{n} {nome}{'s' if n > 1 else ''}" for n, nome in ((h, "hora"), (m, "minuto"), (seg, "segundo")) if n]
    return " e ".join(partes) or "0 segundos"
