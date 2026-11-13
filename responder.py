"""Responder um chat do Claude Code pelo balão do Claudinho (texto ou voz).

O gancho do chat (Stop: terminou; PermissionRequest do AskUserQuestion: pergunta com opções) fica esperando aqui
enquanto você decide. A regra do tempo:

- o balão ainda nem apareceu (fila, resumo sendo feito): até APARECER_S, depois desiste;
- apareceu: dá pra responder na hora, mesmo com ele ainda falando (o relógio fica parado enquanto ele fala e enquanto o
  mouse está em cima, "estou lendo"); terminou de falar: COMECAR_S pra você começar (clicar em "responder", escolher);
- começou: ESCREVER_S pra terminar (dá pra digitar devagar ou falar no microfone).

Desistiu (o tempo acabou, fechou o campo, mandou mensagem pelo próprio app): o chat segue como se o Claudinho não
existisse (termina normal ou a pergunta aparece no app).
"""
import threading
import time

APARECER_S = 150
COMECAR_S = 50
ESCREVER_S = 600
TOTAL_S = 840   # nunca mais que isso (o gancho do Claude Code tem 960 s)


def novo(dados, **extra):
    dados = dados if isinstance(dados, dict) else {}
    return dict({"sid": str(dados.get("session_id") or dados.get("pasta") or "?"),
                 "projeto": str(dados.get("projeto") or "?"), "pasta": str(dados.get("pasta") or ""),
                 "texto": None, "evento": threading.Event(), "criado": time.time()}, **extra)


def prazo(pedido):
    """Até quando o pedido espera, do jeito que ele está agora."""
    if pedido.get("comecou"):
        limite = pedido["comecou"] + ESCREVER_S
    elif pedido.get("mostrado"):
        limite = pedido["mostrado"] + COMECAR_S
    else:
        limite = pedido["criado"] + APARECER_S
    return min(limite, pedido["criado"] + TOTAL_S)


def esperar(pedido, relogio=time.time, passo=0.5):
    """Segura a thread do servidor até a resposta chegar ou o prazo acabar (o prazo muda enquanto espera)."""
    while not pedido["evento"].wait(passo):
        if relogio() > prazo(pedido):
            break
    pedido["evento"].set()


def entregar(pedido, texto):
    if not pedido["evento"].is_set():
        pedido["texto"] = texto
        pedido["evento"].set()


def desistir(pedido):
    if pedido and not pedido["evento"].is_set():
        pedido["texto"] = None
        pedido["evento"].set()


def pendente(pedido):
    return bool(pedido) and not pedido["evento"].is_set()


def comecou(pedido):
    if pedido is not None and not pedido.get("comecou"):
        pedido["comecou"] = time.time()


def mostrado(pedido, de_novo=False):
    """O balão dele apareceu (`de_novo`: você está com o mouse em cima, lendo: o tempo pra começar recomeça)."""
    if pedido is not None and (de_novo or not pedido.get("mostrado")):
        pedido["mostrado"] = time.time()
