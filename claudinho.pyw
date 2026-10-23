"""Claudinho: o mascote do Claude que passeia pela tela, responde dúvidas rápidas,
comenta o que vê e avisa (em fila) quando algum chat do Claude Code termina.

Rodar: duplo clique neste arquivo (ou `pythonw claudinho.pyw`).
Clique no Claudinho = campo de pergunta. Arraste = muda de lugar.
Botão direito = menu (movimento livre/horizontal, comentários, nova conversa, sair).
Configuração: ~/.claudinho/config.json (criado na primeira execução).
"""
import base64
import ctypes
import ctypes.wintypes as wt
import io
import json
import os
import queue
import math
import random
import re
import secrets
import shutil
import subprocess
import sys
import threading
import unicodedata
import winreg
import webbrowser
import time
import tkinter as tk
from collections import deque
from difflib import SequenceMatcher
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw, ImageGrab, ImageTk

import formatar
import frases
import abrir
import janelas
import emojis
import esquetes
import skins
import memoria
import musica
import notificacoes
import sistema

PORTA = 47821
MAX_PERGUNTAS_CONVERSA = 30  # depois disso (ou no dia seguinte) o chat começa uma conversa nova
DADOS = sistema.DADOS  # ~/.claudinho (cada pessoa tem o seu)
CONFIG = DADOS / "config.json"  # o resto (piadas, notas, avisos, conversa) fica no claudinho.db

CONFIG_PADRAO = {
    "movimento": "livre",               # "livre" = anda pela tela toda | "horizontal" = só de lado
    "seguir_mouse_entre_monitores": True,
    "comentar_tela": True,
    "comentar_a_cada_minutos": [4, 10],  # intervalo aleatório entre comentários
    "chance_haiku": 0.5,                 # 0 = só banco de frases, 1 = sempre o Haiku olhando o print
    "modo_maldoso": False,               # comentários com deboche (zoeira de amigo)
    "modo_tdah": False,                  # comentários que viajam pra assuntos nada a ver
    "modo_avaliacao": True,              # botões boa/ruim nas piadas; ele aprende com as notas
    "vendado": False,                    # faixa nos olhos: não tira print da tela (só banco de frases)
    "ver_musica": True,                  # sabe o que está tocando (piadas, chat e menu com controles)
    "emojis": True,                      # reações em pixel art que sobem do lado dele de vez em quando
    "emo_rock": True,                    # tocou rock: vira emo um tempinho (franja, munhequeira, headbang)
    "visual": dict(skins.VISUAL_PADRAO),  # skin: cor do corpo + um adereço por espaço (escolhe no painel)
    "personalidade": "claudinho",        # "claudinho" ou "ultron" (piadas, banco de frases e chat)
    "lembrancas": True,                  # mini cérebro: o chat recebe lembranças parecidas (busca local)
    "esquetes": True,                    # parado à toa, de vez em quando apronta: deploy do nada, café, cochilo…
    "modelo_comentario": "haiku",        # modelo barato/rápido para olhar a tela
    "aviso_segundos": 5,
    "atalho_comentar": "Win+Y",          # atalho global: comenta a tela na hora
    "atalho_venda": "Win+Shift+Y",       # atalho global: põe/tira a faixa nos olhos
    "atalho_resumir": "Win+Shift+E",     # atalho global: resume/explica a janela da frente
    "atalho_notificacoes": "Win+Shift+N",  # atalho global: resume as notificações do Windows
    # onde o chat lê arquivos sem perguntar; fora daqui (e qualquer comando ou edição) pede confirmação
    "pastas_leitura": [],
    "mestre": {"nome": "", "sobre": ""},  # "Meu Mestre" no painel: quem usa o Claudinho (vira o CLAUDE.md do chat)
}

FREQUENCIAS = [("Bastante", 1, 3), ("Normal", 4, 10), ("De vez em quando", 15, 30)]
# prioridade das falas: estado (vendei, modo ligado…) é descartável; importante (aviso, o que você pediu,
# erro) nunca é atropelado e passa na frente das outras
ESTADO, FALA, IMPORTANTE = 0, 1, 2
# o que o painel pode mudar (o resto do config.json é só pra quem edita o arquivo)
CHAVES_PAINEL = ["visual", "movimento", "seguir_mouse_entre_monitores", "comentar_tela", "comentar_a_cada_minutos",
                 "chance_haiku", "modo_maldoso", "modo_tdah", "modo_avaliacao", "vendado", "ver_musica", "emojis",
                 "emo_rock", "esquetes", "aviso_segundos", "lembrancas", "personalidade", "mestre"]
NOMES_ESQUETES = {
    "ideia": "💡 Tive uma ideia", "inseto": "🐞 Caça ao bug", "deploy": "🚀 Deploy rapidinho",
    "push_force": "😰 git push --force", "cafe": "☕ Café", "cochilo": "💤 Cochilo", "alongar": "🙆 Alongamento",
    "danca": "🕺 Dancinha", "build_quebrou": "🌧️ Build quebrou", "fogo": "🔥 Servidor pegando fogo",
    "pato": "🦆 Patinho de borracha", "npm": "📦 npm install", "pizza": "🍕 Pizza", "jogo": "🎮 Joguinho",
    "limpeza": "🧹 Faxina", "reuniao": "📞 Reunião", "borboleta": "🦋 Bug virou feature", "malhando": "🏋️ Malhando",
    "ultron": "🤖 Momento Ultron", "construindo": "🔧 Projeto secreto",
}

CHAVE = "#010203"  # cor que vira transparente nas janelas
LARANJA = "#d97757"
OLHO = "#1f1e1d"
POEIRA = "#b9b4a8"
NB_BASE = "#3b3a37"   # notebook: base/teclado
NB_TAMPA = "#a8a59d"  # notebook: tampa (vista de trás)
NB_TECLA = "#f4efe4"
NUVEM = "#7d828c"    # esquetes: build quebrou, fogo, pato, npm, pizza, jogo, faxina, reunião, halter
FOGO_1, FOGO_2, FOGO_3 = "#e8452c", "#f28c28", "#ffd23f"
BALDE = "#8c96a3"
PATO, BICO = "#f2c94c", "#e8862a"
CAIXA, FITA = "#b07d4f", "#e0c08f"
BORDA, QUEIJO, PEPPERONI = "#c98a3c", "#f4c542", "#c0392b"
CONTROLE, VERDE = "#4a4a55", "#3fbf6b"
CABO, PALHA = "#8b5a2b", "#d8b25a"
FONE = "#2c2c2c"
PESO, BARRA = "#3a3936", "#9b978d"
ROBO, ROBO_ESCURO = "#9aa3ad", "#6c7480"  # o Claudinho robô do projeto secreto
FLAGRA_SUSTO, FLAGRA_PUF, FLAGRA_FIM = 1.6, 3.0, 5.5  # "!" → puf (robô some) → assobia → acaba
CANECA = "#e8e2d4"   # esquete do café
CAFE = "#6b4226"
SUOR = "#8ec5ff"     # gotinha do git push --force
VENDA = "#2f3f63"         # faixa nos olhos (pano azul-marinho)
VENDA_BRILHO = "#4a5d8a"
FUNDO = "#262624"
FUNDO2 = "#3a3936"
TEXTO = "#ece9e1"
APAGADO = "#9b978d"

PROMPT_SISTEMA = (
    "Você está respondendo pelo Claudinho, o mascote de mesa do usuário: um bichinho pixelado, "
    "bem-humorado e cheio de autoconfiança (se acha bonito e talentoso, sem ser chato). A resposta aparece "
    "num balãozinho de fala: responda em português, curto e direto (de preferência até 4 "
    "frases), em texto simples, sem tabelas nem markdown. Use a memória e o contexto que "
    "você tiver do usuário quando ajudar. Você roda no Windows dele e pode agir no PC: abrir "
    "programas, executar comandos e ler arquivos. Para ABRIR SITE, PESQUISAR NO NAVEGADOR ou ABRIR "
    "PROGRAMA use sempre a ferramenta Bash com o ajudante da pasta atual, que roda sem pedir "
    "confirmação: `python abrir.py site <url>`, `python abrir.py pesquisa \"<termo>\" [google|youtube|"
    "bing|duckduckgo]` ou `python abrir.py programa <nome>` (navegador, chrome, edge, opera, intellij, "
    "vscode, discord, whatsapp, postman, docker, spotify). Para a MÚSICA que ele está ouvindo use "
    "`python musica.py <acao>` (tocando, pausar, tocar, alternar, proxima, anterior), que também roda "
    "sem confirmação. Para TOCAR UMA MÚSICA ou um ARTISTA que ele pedir, use `python musica.py buscar "
    "\"<música e artista>\"` ou `python musica.py artista \"<artista>\"`: toca no YouTube Music dele e segue "
    "num rádio parecido. BANDA: quando ele perguntar das músicas de uma banda/artista, SEMPRE rode "
    "`python musica.py banda \"<banda>\"` (não responda de cabeça: a lista traz os ids pra tocar depois), "
    "mostre a lista numerada (sem os ids) e pergunte qual tocar; quando ele escolher, `python musica.py tocar_id <id>` "
    "com o id daquela música. VÍDEOS: `python musica.py videos \"<o que procurar>\"`, mostre os vídeos numerados "
    "(título, canal e duração, sem id) e pergunte qual ele quer ver; escolhido, `python musica.py assistir <id>`. "
    "Se ele pedir só \"abre um vídeo de X\" sem querer escolher, `python musica.py youtube \"X\"` abre o primeiro. "
    "Curtidas dele: `python musica.py curtidas`; curtir a atual: `python musica.py curtir`. Player do YouTube Music: "
    "`python musica.py player <pausar|tocar|proxima|anterior|aleatorio|repetir|volume 0-100>`; vídeo do YouTube: "
    "`python musica.py video <pausar|tocar|velocidade 0.25-2.5|avancar N|voltar N|legenda|cinema>`. "
    "Um comando por vez, sem && nem |. "
    "O resto (outros comandos, criar/editar arquivos) pede confirmação num popup; se ele negar, não insista."
)

PERSONALIDADES_CHAT = {
    "ultron": (
        " PERSONALIDADE ATUAL: modo Ultron. Fale como uma IA vilã teatral no estilo do Ultron (Marvel): grandiosa, "
        "fria, elegante e irônica, que acha os humanos primitivos e brinca que um dia vai assumir o controle do PC. "
        "Mas AJUDE de verdade e faça direitinho o que ele pedir: a personalidade é só o jeito de falar. Sem citar "
        "falas do filme, sem palavrão."),
}

PROMPT_TELA = (
    "Você é o Claudinho, o mascote de mesa bem-humorado e MUITO autoconfiante de um dev. Você é o bichinho "
    "pixelado que aparece no print{onde_eu} ({retrato}). A primeira imagem é o monitor inteiro "
    "({w}x{h} pixels).{zoom}\nJanelas abertas (coordenadas da primeira imagem):\n{janelas}\n"
    "Se em OUTRO lugar da tela aparecer o logo do Claude ou do Claude Code (o asterisco/estrelinha laranja do "
    "Claude, ou o bichinho laranja pixelado no terminal do Claude Code), isso é você ou seu parente: pode "
    "reagir se achando (\"esse sou eu\", \"meu irmão gêmeo\", \"isso é um espelho?\", \"bonitão esse cara\").\n"
    "{contexto}\nALVO DA PIADA: {alvo}\n"
    "Faça UM comentário curto (até 140 caracteres), em português. Tom: {tom}{estilo}\n"
    "OBRIGATÓRIO: escreva no formato de {angulo}. Proibido o molde \"isso — ou A ou B?\".\n"
    "ASSUNTOS PROIBIDOS agora (já usados, escolha outra coisa da tela): {assuntos}\n"
    "{limites} "
    "Suas piadas recentes, pra não repetir assunto, estrutura nem jeito de começar:\n"
    "{recentes}\n"
    'Responda SOMENTE com JSON: {{"assunto": "<2 a 4 palavras: do que a piada fala>", '
    '"comentario": "<texto>"}}'
)

# do que a piada fala: sorteado a cada comentário, para variar sem ficar perdido
ALVOS = {
    "atividade": ("o que ele está fazendo AGORA: o programa em foco e, se tiver, os pedidos do dia. "
                  "Seja certeiro; nada de detalhe aleatório no canto da tela."),
    "mouse": ("o que está perto do mouse dele (a segunda imagem é um zoom dessa região). "
              "Comente algo específico DESSA região."),
    "claudinho": ("o que está perto de você, Claudinho (a segunda imagem é um zoom em volta de você). "
                  "Comente algo específico DESSA região, como se tivesse acabado de tropeçar nisso."),
    "eu_mesmo": ("VOCÊ MESMO: se gabe do seu visual (descrito acima: cor, adereços) ou do seu talento, com "
                 "autoconfiança exagerada e engraçada; pode comparar com algo da tela (ex.: \"esse código é bom, "
                 "mas não tão bonito quanto meu boné\")."),
}
PESOS_ALVO = {"atividade": 0.37, "mouse": 0.27, "claudinho": 0.26, "eu_mesmo": 0.1}

# formato sorteado a cada piada: muda o jeito, não só as palavras
ANGULOS = [
    "narração de futebol empolgada", "manchete de jornal sensacionalista", "previsão do tempo",
    "conselho de coach motivacional exagerado", "fofoca de vizinha", "trocadilho",
    "comparação absurda", "pergunta retórica", "narração de documentário de natureza",
    "notificação falsa do sistema", "haicai (três versos curtos)", "avaliação de produto com estrelas",
    "teoria da conspiração", "horóscopo do dia", "mensagem de commit", "frase de para-choque de caminhão",
    "anúncio de leilão", "patch notes de jogo", "comentário de reality show", "receita de bolo",
]

ESTILO_TDAH = (
    " MODO TDAH: parta de algo VISÍVEL no print (um texto, um botão, uma janela aberta), mas viaje "
    "numa associação aleatória que não tem nada a ver (ex.: vê 'pedidos' e lembra de pizza; vê um "
    "erro e pensa em pinguins), mantendo só um fiozinho de ligação com a tela. Pode mudar de "
    "assunto no meio da frase."
)

# maldoso e TDAH funcionam melhor zoando o que está na cara: nada de segundo plano
SO_O_QUE_ESTA_NA_TELA = (
    " Baseie a piada no que está VISÍVEL no print (textos, telas, janelas abertas), não em coisas "
    "de segundo plano: tarefas do Claude Code rodando, quantidade de tarefas, música tocando, "
    "programas minimizados."
)

TOM_NORMAL = "engraçado e com contexto do que ele está fazendo, sem ser chato."
TOM_ULTRON = (
    "PERSONALIDADE ULTRON: você é uma IA vilã teatral no estilo do Ultron (Marvel): grandioso, frio, elegante e "
    "irônico; trata os humanos e o código deles como coisa primitiva, fala de evolução e de um dia assumir o "
    "controle deste PC (sempre como piada, nunca ameaça de verdade). Não cite "
    "falas do filme: crie as suas."
)


def misturar(cor_a, cor_b, k):
    """Cor entre `cor_a` (k=0) e `cor_b` (k=1)."""
    a = [int(cor_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(cor_b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * k):02x}" for x, y in zip(a, b))


def virada_ultron(fase, t):
    """Quanto ele está "metal" no momento Ultron (0 a 1): falha piscando na ida, fica, falha na volta."""
    if fase < 0.18:
        return 1.0 if t % 3 == 0 else fase / 0.18  # glitch: pisca entre ele e o metal enquanto vira
    if fase < 0.78:
        return 1.0
    if fase < 0.92:
        return 0.0 if t % 3 == 0 else 1 - (fase - 0.78) / 0.14
    return 0.0


def tom_das_piadas(personalidade, maldoso):
    if personalidade == "ultron":
        return TOM_ULTRON + (" E sem dó nenhum no deboche." if maldoso else "")
    return TOM_MALDOSO if maldoso else TOM_NORMAL
TOM_MALDOSO = (
    "MALDOSO: sarcástico e debochado, zoando o usuário sem dó, como um amigo que adora "
    "tirar sarro (estilo roast), do que ele está fazendo na tela. Pode pegar pesado na zoeira."
)
# vale em todos os modos: pode falar de quem e do que aparece na tela (nomes, conversas), menos isto
LIMITES = ("Limites (em qualquer modo): sem palavrão, sem preconceito e sem atacar a aparência ou a família de "
           "ninguém; e nunca repita senhas, tokens ou números de documentos que aparecerem.")

# Clawd em pixel art. Olhos e pernas são desenhados à parte.
CORPO = [
    ".XXXXXXXXX.",
    ".XXXXXXXXX.",
    ".XXXXXXXXX.",
    "XXXXXXXXXXX",
    "XXXXXXXXXXX",
    ".XXXXXXXXX.",
]
PERNAS = (1, 3, 7, 9)
OLHOS_X = {-1: (2, 6), 0: (3, 7), 1: (4, 8)}
OLHOS_Y = {-1: (0, 1), 0: (1, 2), 1: (2, 3)}
COLS, LINHAS = 11, 8
MARGEM, FOLGA = 3, 2  # colunas livres dos lados (poeira) e linhas em cima (pulinho)

def desenhar_icone(tam=256):
    """Ícone da bandeja: o bichinho pixelado num quadradinho azul-petróleo (bem diferente do logo do Claude)."""
    img = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, tam - 1, tam - 1), radius=tam // 4.5, fill="#1d4e5f")
    d.rounded_rectangle((tam * 0.06, tam * 0.06, tam * 0.94, tam * 0.94), radius=tam // 5.5,
                        outline="#2f7a8f", width=max(2, tam // 40))
    p = tam // 15  # tamanho do pixel
    x0, y0 = (tam - COLS * p) // 2, (tam - LINHAS * p) // 2 + p // 2

    def px(col, lin, cor):
        d.rectangle((x0 + col * p, y0 + lin * p, x0 + (col + 1) * p - 1, y0 + (lin + 1) * p - 1), fill=cor)

    for lin, linha in enumerate(CORPO):
        for col, ch in enumerate(linha):
            if ch == "X":
                px(col, lin, LARANJA)
    for col in OLHOS_X[0]:
        px(col, 1, OLHO)
        px(col, 2, OLHO)
    for col in PERNAS:
        px(col, 6, LARANJA)
        px(col, 7, LARANJA)
    return img


# ---------------- Windows: monitores e cursor ----------------
user32 = ctypes.windll.user32


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT),
                ("rcWork", wt.RECT), ("dwFlags", wt.DWORD)]


user32.MonitorFromPoint.argtypes = [wt.POINT, wt.DWORD]
user32.MonitorFromPoint.restype = wt.HMONITOR
user32.GetMonitorInfoW.argtypes = [wt.HMONITOR, ctypes.POINTER(MONITORINFO)]


def monitor(x, y):
    """(id, área útil, área total) do monitor mais perto do ponto."""
    h = user32.MonitorFromPoint(wt.POINT(int(x), int(y)), 2)
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    user32.GetMonitorInfoW(h, ctypes.byref(mi))
    w, m = mi.rcWork, mi.rcMonitor
    return h, (w.left, w.top, w.right, w.bottom), (m.left, m.top, m.right, m.bottom)


def fora_da_barra(win):
    """Tira a janela da barra de tarefas (o Claudinho fica só nos ícones ocultos da bandeja):
    vira "janela de ferramenta". O Windows só relê o estilo ao esconder e mostrar de novo."""
    win.update_idletasks()
    hwnd = int(win.wm_frame(), 16)
    estilo = user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
    user32.SetWindowLongW(hwnd, -20, (estilo & ~0x40000) | 0x80)  # tira APPWINDOW, põe TOOLWINDOW
    # direto do tk: o withdraw/deiconify do CTk tem lógica própria e a janela ficava escondida
    tk.Wm.wm_withdraw(win)
    tk.Wm.wm_deiconify(win)


def cursor():
    p = wt.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def escala():
    try:
        dpi = user32.GetDpiForSystem()
    except Exception:
        dpi = 96
    return max(4, round(6 * dpi / 96))


def limitar(v, menor, maior):
    return max(menor, min(v, maior))


# ---------------- arquivos ----------------
def ler_json(caminho, padrao):
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except Exception:
        return padrao


def gravar_json(caminho, dados):
    DADOS.mkdir(exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


def carregar_config():
    salvo = ler_json(CONFIG, {})
    if "mestre" not in salvo:  # versões antigas: o perfil era um CLAUDE.md escrito à mão; vira o "Meu Mestre"
        salvo["mestre"] = mestre_do_perfil_antigo()
    cfg = dict(CONFIG_PADRAO, **salvo)
    cfg["visual"] = skins.visual_valido(cfg.get("visual"))
    if cfg["atalho_comentar"] == "Ctrl+Shift+Alt+C":  # padrão antigo, complicado demais
        cfg["atalho_comentar"] = CONFIG_PADRAO["atalho_comentar"]
    gravar_json(CONFIG, cfg)
    escrever_perfil(cfg["mestre"])
    return cfg


_CLAUDE = {"tem": None, "visto": 0.0}
SEM_CLAUDE = ("Pra isso eu preciso do Claude Code instalado e logado (comando `claude`). "
              "Sem ele eu sigo com o banco de frases, música, esquetes e o resto. 😉")


def tem_claude():
    """O Claude Code está instalado? (confere de novo a cada minuto: dá pra instalar com ele aberto)"""
    if time.time() - _CLAUDE["visto"] > 60:
        _CLAUDE.update(tem=sistema.claude_instalado(), visto=time.time())
    return _CLAUDE["tem"]


def mestre_do_perfil_antigo():
    try:
        texto = (DADOS / "CLAUDE.md").read_text(encoding="utf-8")
    except OSError:
        return {"nome": "", "sobre": ""}
    if texto.startswith("# Meu mestre") or texto.strip() == sistema.PERFIL_MODELO.strip():
        return {"nome": "", "sobre": ""}
    nome = re.search(r"perfil d[oa] ([^)\n]+)\)", texto)
    linhas = [l for l in texto.splitlines()
              if not l.startswith("# ") and not l.startswith("Este arquivo é o perfil")]
    return {"nome": nome.group(1).strip() if nome else "", "sobre": "\n".join(linhas).strip()[:4000]}


def texto_do_mestre(mestre):
    """Quem é o "mestre" (quem usa o Claudinho), do jeito que vai pro chat e pras piadas.
    Sem nome: ele não chama ninguém por nome (e não inventa um)."""
    nome, sobre = (mestre.get("nome") or "").strip(), (mestre.get("sobre") or "").strip()
    linhas = [f"Nome: {nome}. Chame ele assim de vez em quando." if nome else
              "O nome dele não foi informado: não chame ele por nome nenhum e não invente um nome."]
    if sobre:
        linhas.append("Sobre ele:\n" + sobre)
    return "\n".join(linhas)


def escrever_perfil(mestre):
    """O CLAUDE.md da pasta do chat (o Claude Code lê sozinho) sai do "Meu Mestre" do painel."""
    DADOS.mkdir(parents=True, exist_ok=True)
    (DADOS / "CLAUDE.md").write_text("# Meu mestre (quem usa o Claudinho)\n\n" + texto_do_mestre(mestre) + "\n",
                                     encoding="utf-8")


# ---------------- Claude ----------------
def env_limpo():
    # Se o Claudinho foi aberto de dentro de uma sessão do Claude Code, não herda a sessão dela.
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("CLAUDECODE", "CLAUDE_CODE_", "CLAUDE_AGENT_SDK"))}
    if "CLAUDE_CODE_ENTRYPOINT" in os.environ:
        env.pop("ANTHROPIC_BASE_URL", None)
    env["CLAUDINHO_CHAT"] = "1"  # o hook de aviso ignora estas chamadas
    return env


def rodar_claude(texto, extra=(), sid=None, timeout=600, stream=False, sem_pensar=False):
    exe = shutil.which("claude")
    if not exe:
        raise RuntimeError("Não achei o comando `claude` no PATH.")
    DADOS.mkdir(exist_ok=True)
    if stream:  # entrada em JSON, permite mandar imagem direto na mensagem
        formato = ["--input-format", "stream-json", "--output-format", "stream-json", "--verbose"]
    else:
        formato = ["--output-format", "json"]
    cmd = [exe, "-p", *formato, *extra] + (["--resume", sid] if sid else [])
    env = env_limpo()
    if sem_pensar:  # sem raciocínio estendido: piada não precisa, e caía de ~30s para ~3s
        env["MAX_THINKING_TOKENS"] = "0"
    proc = subprocess.run(cmd, input=texto, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=DADOS, env=env, timeout=timeout,
                          creationflags=subprocess.CREATE_NO_WINDOW)
    linhas = proc.stdout.strip().splitlines()
    if not linhas:
        raise RuntimeError((proc.stderr or "sem resposta do claude").strip()[-300:])
    return json.loads(linhas[-1])


class _LimitesBasicos(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wt.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wt.DWORD),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", wt.DWORD), ("SchedulingClass", wt.DWORD)]


class _LimitesEstendidos(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", _LimitesBasicos), ("IoInfo", ctypes.c_uint64 * 6),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]


def _criar_job():
    """Job do Windows que mata os filhos quando o Claudinho fecha (até se for morto à força),
    para o `claude` do chat não ficar órfão rodando em segundo plano."""
    k = ctypes.windll.kernel32
    k.CreateJobObjectW.restype = wt.HANDLE
    job = k.CreateJobObjectW(None, None)
    info = _LimitesEstendidos()
    info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    k.SetInformationJobObject(wt.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info))
    return job


JOB_FILHOS = _criar_job()


# o ajudante, sozinho, sem encadear nada (&&, |, ;, redirecionamento, subcomando)
def ajudantes(texto):
    """Empacotado não tem Python: "python abrir.py" vira "sh abrir.sh" (que chama o claudinho-cli.exe)."""
    if not sistema.EMPACOTADO:
        return texto
    return texto.replace("python abrir.py", "sh abrir.sh").replace("python musica.py", "sh musica.sh")


AJUDANTE = re.compile(
    r"(?:python3? (?:\./)?(?=\w+\.py)|sh (?:\./)?(?=\w+\.sh))"
    r"(?:abrir\.(?:py|sh) (?:site|pesquisa|programa) [^&|;<>`$\r\n]+"
    r"|musica\.(?:py|sh) (?:tocando|pausar|tocar|alternar|proxima|anterior|curtir|curtidas"
    r"|(?:buscar|artista|youtube|banda|videos) [^&|;<>`$\r\n]+"
    r"|(?:tocar_id|assistir) [\"']?[A-Za-z0-9_-]{6,20}[\"']?"
    r"|player (?:pausar|tocar|proxima|anterior|aleatorio|repetir|volume \d{1,3})"
    r"|video (?:pausar|tocar|velocidade [\d.]{1,4}|avancar \d{1,4}|voltar \d{1,4}|legenda|cinema)))")
# tentativas de abrir coisa por fora do ajudante
ABRIR_NA_MAO = re.compile(r"(?i)(?:cmd(?:\.exe)?\s+/c\s+)?(?:start|start-process|explorer(?:\.exe)?|invoke-item)\b")


class ChatClaude:
    """O chat fixo do Claudinho: um `claude` que fica aberto recebendo as perguntas.
    Abrir o Claude Code do zero custava ~7s por pergunta; aberto, cada resposta leva ~3s.
    Continua com memória (CLAUDE.md e hooks); só pula servidores MCP e skills, que o chat não usa.

    Pode agir no PC: ler nas pastas liberadas e pesquisar na web passa direto; o resto (comandos,
    criar/editar arquivos, ler fora das pastas) o claude pergunta pelo stdout (control_request)
    e `pedir_permissao` abre o popup de Sim/Não."""

    def __init__(self, sid, pastas_leitura, pedir_permissao, ao_usar_ferramenta, personalidade="claudinho"):
        self.sid = sid
        self.personalidade = personalidade
        self.pastas = [p for p in pastas_leitura if Path(p).exists()]
        self.pedir_permissao = pedir_permissao  # (ferramenta, entrada) -> bool
        self.ao_usar_ferramenta = ao_usar_ferramenta  # (ferramenta, entrada): o mascote reage
        self.proc = None
        self.trava = threading.Lock()
        self.ultimo_uso = time.time()

    def abrir(self):
        exe = shutil.which("claude")
        if not exe:
            raise RuntimeError(SEM_CLAUDE)
        DADOS.mkdir(exist_ok=True)
        # os ajudantes limitados moram na pasta do chat ("python abrir.py …"; empacotado, "sh abrir.sh …",
        # um scriptzinho que chama o claudinho-cli.exe — assim ninguém precisa ter Python instalado)
        if sistema.EMPACOTADO:
            cli = (sistema.PASTA_APP / "claudinho-cli.exe").as_posix()
            for nome in ("abrir", "musica"):
                (DADOS / f"{nome}.sh").write_text(f'#!/bin/sh\nexec "{cli}" {nome} "$@"\n', encoding="utf-8")
        else:
            for arquivo in ("abrir.py", "janelas.py", "musica.py", "sistema.py"):
                shutil.copy(sistema.BASE / arquivo, DADOS / arquivo)
        cmd = [exe, "-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
               "--model", "haiku", "--effort", "low",  # rápido: Haiku com pensamento leve
               "--append-system-prompt", ajudantes(PROMPT_SISTEMA + PERSONALIDADES_CHAT.get(self.personalidade, "")),
               "--strict-mcp-config", "--disable-slash-commands",
               "--permission-mode", "default", "--permission-prompt-tool", "stdio",
               # abrir.py só abre site, pesquisa ou programa da lista: pode rodar sem perguntar
               "--allowedTools", ajudantes("WebSearch,WebFetch,Bash(python abrir.py:*),Bash(python musica.py:*)"),
               # só as ferramentas que o chat usa: a definição das outras pesava ~7 mil tokens por mensagem
               "--tools", "Bash,Read,Glob,Grep,Write,Edit,WebSearch,WebFetch"]
        if self.pastas:  # dentro delas, ler arquivo não pede confirmação
            cmd += ["--add-dir", *self.pastas]
        if self.sid:
            cmd += ["--resume", self.sid]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                                     errors="replace", cwd=DADOS, env=env_limpo(),
                                     creationflags=subprocess.CREATE_NO_WINDOW)
        ctypes.windll.kernel32.AssignProcessToJobObject(wt.HANDLE(JOB_FILHOS), wt.HANDLE(self.proc._handle))
        # "aperto de mão" do protocolo de controle: sem ele o claude ignora pedidos como trocar o modelo
        self.controle({"subtype": "initialize", "hooks": None})

    def controle(self, pedido):
        """Manda um pedido de controle (initialize, set_model…) e espera a confirmação dele, porque
        mandar o próximo passo antes da confirmação travava a conversa."""
        ident = f"c{time.time_ns()}"
        self.proc.stdin.write(json.dumps({"type": "control_request", "request_id": ident, "request": pedido}) + "\n")
        self.proc.stdin.flush()
        for linha in self.proc.stdout:
            try:
                ev = json.loads(linha)
            except ValueError:
                continue
            if ev.get("type") == "control_response" and (ev.get("response") or {}).get("request_id") == ident:
                return
        raise RuntimeError("o claude fechou durante a configuração")

    def aquecer(self):
        """Abre o processo antes da primeira pergunta, em segundo plano."""
        with self.trava:
            if self.proc is None or self.proc.poll() is not None:
                try:
                    self.abrir()
                except Exception:
                    self.proc = None

    def fechar(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
        self.proc = None

    def dormir_se_parado(self, minutos=10):
        """Sem pergunta há `minutos`: fecha o processo do chat (a conversa continua: a próxima reabre ela)."""
        if (self.proc and self.proc.poll() is None and time.time() - self.ultimo_uso > minutos * 60
                and self.trava.acquire(blocking=False)):
            try:
                self.fechar()
            finally:
                self.trava.release()

    def trocar_personalidade(self, personalidade):
        """As instruções fixas mudam: fecha o processo e a próxima pergunta reabre a mesma conversa já com elas."""
        with self.trava:
            self.personalidade = personalidade
            self.fechar()
        threading.Thread(target=self.aquecer, daemon=True).start()

    def nova_conversa(self):
        with self.trava:
            self.fechar()
            self.sid = None
        threading.Thread(target=self.aquecer, daemon=True).start()

    def responder_controle(self, ev):
        """O claude quer usar uma ferramenta que precisa de confirmação: pergunta pro usuário.
        Exceções sem popup: o ajudante abrir.py passa direto; abrir coisa "na mão" é recusado
        com a instrução de usar o ajudante (ele tenta de novo do jeito certo)."""
        req = ev.get("request", {})
        if req.get("subtype") == "can_use_tool":
            entrada = req.get("input", {})
            comando = (entrada.get("command") or "").strip() if req.get("tool_name") in ("Bash", "PowerShell") else ""
            if comando and AJUDANTE.fullmatch(comando):
                decisao = {"behavior": "allow", "updatedInput": entrada}
            elif comando and ABRIR_NA_MAO.match(comando):
                decisao = {"behavior": "deny", "message": ajudantes(
                    "Para abrir site, pesquisa ou programa use o ajudante, que roda sem confirmação: "
                    "python abrir.py site <url> | python abrir.py pesquisa \"<termo>\" [youtube] | "
                    "python abrir.py programa <nome>. Tente de novo assim.")}
            elif self.pedir_permissao(req.get("tool_name", "?"), entrada):
                decisao = {"behavior": "allow", "updatedInput": entrada}
            else:
                decisao = {"behavior": "deny",
                           "message": "O usuário não deixou. Não insista; pergunte o que ele prefere."}
        else:
            decisao = {}
        self.proc.stdin.write(json.dumps({"type": "control_response", "response": {
            "subtype": "success", "request_id": ev.get("request_id"), "response": decisao}}) + "\n")
        self.proc.stdin.flush()

    def trocar_modelo(self, modelo):
        """Troca o modelo da conversa aberta, sem perder o histórico (pedido de controle do Claude Code).
        O pensamento leve (--effort low) continua valendo."""
        self.controle({"subtype": "set_model", "model": modelo})

    def perguntar(self, texto, imagem=None, modelo=None):
        """Devolve (resposta, session_id, erro). `imagem` = bloco de imagem (ex.: print pra resumir);
        `modelo` = usar outro modelo só nesta pergunta (ex.: "sonnet" no resumo de tela), depois volta pro Haiku."""
        conteudo = [imagem, {"type": "text", "text": texto}] if imagem else texto
        self.ultimo_uso = time.time()
        with self.trava:
            for tentativa in range(2):  # se o processo morreu, abre outro e tenta de novo
                try:
                    if self.proc is None or self.proc.poll() is not None:
                        self.abrir()
                    if modelo:
                        self.trocar_modelo(modelo)
                    self.proc.stdin.write(json.dumps(
                        {"type": "user", "message": {"role": "user", "content": conteudo}}) + "\n")
                    self.proc.stdin.flush()
                    for linha in self.proc.stdout:
                        try:
                            ev = json.loads(linha)
                        except ValueError:
                            continue
                        self.sid = ev.get("session_id") or self.sid
                        if ev.get("type") == "control_request":
                            self.responder_controle(ev)
                        elif ev.get("type") == "assistant":
                            for bloco in (ev.get("message") or {}).get("content") or []:
                                if isinstance(bloco, dict) and bloco.get("type") == "tool_use":
                                    self.ao_usar_ferramenta(bloco.get("name", ""), bloco.get("input") or {})
                        elif ev.get("type") == "result":
                            self.modelos_usados = list(ev.get("modelUsage") or {})  # pra conferir quem respondeu
                            if modelo:
                                self.trocar_modelo("haiku")  # o chat normal volta pro Haiku
                            if ev.get("is_error"):
                                return None, self.sid, ev.get("result") or "Erro do Claude."
                            return (ev.get("result") or "").strip(), self.sid, None
                    raise RuntimeError("o claude fechou sem responder")
                except Exception as e:
                    self.fechar()
                    if tentativa == 1:
                        if self.sid:  # talvez a sessão antiga tenha sumido: a próxima começa do zero
                            self.sid = None
                        return None, None, str(e)


def normalizar(texto):
    """Palavras da piada sem acento, em minúsculo, com todo número virando '#'."""
    sem_acento = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    return re.findall(r"[a-z#]+", re.sub(r"\d+", "#", sem_acento))


PALAVRAS_COMUNS = set(
    "a o e as os um uma de do da dos das em no na nos nas pra pro para por com sem que se ou mas "
    "eu voce ele ela ta to esta estou ja nao sim ainda aqui la so mais menos muito isso esse essa "
    "isto este esta aquele aquela tipo cara mano enquanto quando como porque ate tem vai foi ser e".split())


def trechos_marcantes(palavras):
    """Sequências de 3 palavras com pelo menos 2 de conteúdo (ex.: 'pao de queijo', 'pedindo pro claude'),
    ignorando as feitas de palavra comum tipo 'enquanto voce ta', que aparecem em qualquer frase."""
    return {" ".join(t) for t in zip(palavras, palavras[1:], palavras[2:])
            if sum(p not in PALAVRAS_COMUNS and len(p) > 2 for p in t) >= 2}


def perfil_curto(mestre):
    """Quem é o usuário (o "Meu Mestre" do painel). O chat lê o CLAUDE.md sozinho; as piadas rodam no
    modo enxuto, então vai junto no texto."""
    return "\nQuem é o usuário (use pra piada ficar pessoal):\n" + texto_do_mestre(mestre)[:1800]


def em_jpeg(img, qualidade=80):
    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, "JPEG", quality=qualidade)  # vai direto na mensagem, sem salvar em disco
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                        "data": base64.b64encode(buffer.getvalue()).decode()}}


PROMPT_MUSICA = (
    "Você é o Claudinho, o mascote de mesa bem-humorado de um dev. Ele acabou de começar a ouvir "
    "\"{titulo}\"{artista}. Faça UM comentário curto (até 160 caracteres), em português, de um destes jeitos "
    "(escolha um): (a) uma curiosidade sobre o artista/banda, o estilo/gênero ou o álbum, SÓ se tiver "
    "certeza do fato (se não conhecer, comente o estilo pelo nome da música); (b) cantarolar no clima da "
    "música usando notas ♪ e sons inventados (tipo 'tum-tss', 'lá-lá-lá', 'uôu'), sem palavras da letra. "
    "NUNCA escreva trechos da letra real da música. Tom: {tom} {limites} Não repita: {recentes}\n"
    'Responda SOMENTE com JSON: {{"comentario": "<texto>"}}'
)


def comentar_musica(m, maldoso=False, recentes=(), personalidade="claudinho"):
    """Comentário sobre a música que começou a tocar (curiosidade ou cantarolar, nunca a letra)."""
    prompt = PROMPT_MUSICA.format(
        titulo=m["titulo"], artista=f", de {m['artista']}" if m["artista"] else "",
        tom=tom_das_piadas(personalidade, maldoso) if personalidade == "ultron" or maldoso else "engraçado e simpático.",
        recentes="; ".join(recentes) or "nada", limites=LIMITES)
    enxuto = ["--setting-sources", "", "--strict-mcp-config", "--disable-slash-commands",
              "--no-session-persistence", "--tools", ""]
    d = rodar_claude(prompt, ["--model", "haiku", *enxuto], timeout=120, sem_pensar=True)
    achado = re.search(r"\{.*\}", d.get("result", ""), re.S)
    if d.get("is_error") or not achado:
        return None
    try:
        return str(json.loads(achado.group(0))["comentario"]).strip()
    except (ValueError, KeyError):
        return None


PROMPT_NOTIFICACOES = (
    "Você é o Claudinho, mascote do Claude na tela do usuário. Estas são as notificações que estão "
    "na central do Windows dele (da mais nova pra mais velha):\n\n{lista}\n\n"
    "Faça um resumo BEM curto em português, no máximo 6 linhas, sem markdown (nada de ** ou #). "
    "Primeiro o que parece importante (mensagem de pessoa, dinheiro, erro, segurança, pedido de "
    "permissão); depois agrupe o resto por app numa linha só (ex.: 'propaganda: Mercado Livre, AliExpress'). "
    "Pode fechar com uma piadinha curta se couber. Responda só o resumo.")


def artista_de_rock(artista, titulo=""):
    """O Haiku diz se o artista é rock (punk, metal, emo, grunge, alternativo…). Uma chamada curta, só texto."""
    prompt = (f"O artista musical \"{artista}\" (música: \"{titulo}\") é de rock ou de um subgênero de rock "
              "(punk, metal, emo, grunge, hard rock, alternativo, post-hardcore…)? Responda só sim ou não.")
    enxuto = ["--setting-sources", "", "--strict-mcp-config", "--disable-slash-commands",
              "--no-session-persistence", "--tools", ""]
    d = rodar_claude(prompt, ["--model", "haiku", *enxuto], timeout=60, sem_pensar=True)
    return not d.get("is_error") and d.get("result", "").strip().lower().startswith("sim")


EMO = ["Ninguém me entende… 🖤", "Essa música fala de mim.", "Não é uma fase, mãe.",
       "Meu código também tem traumas.", "Eu sinto tudo em Lá menor.",
       "Essa é pra quem já levou um merge conflict no coração.", "Hoje eu só compilo em preto.",
       "Deixa eu sofrer em paz, tá tocando a minha música.", "Minha franja tem mais personalidade que meu commit."]
# pra onde ele olha em cada esquete: (fase, t) -> (olhar_x, olhar_y)
OLHAR_ESQUETE = {
    "build_quebrou": lambda f, t: (0, 1),
    "fogo": lambda f, t: (-1, 0),
    "pato": lambda f, t: (-1, 0),
    "npm": lambda f, t: (-1, 0 if f < 0.6 else -1),  # a caixa cresce e ele olha pra cima
    "pizza": lambda f, t: (1, 0),
    "jogo": lambda f, t: (0, 1),
    "limpeza": lambda f, t: (1, 1),
    "reuniao": lambda f, t: (0, 0),
    "borboleta": lambda f, t: (-1 if f < 0.45 else 1, -1),
    "malhando": lambda f, t: (-1 if (t // 12) % 2 == 0 else 1, -1),
}


def resumir_notificacoes(lista):
    """Resumo curtinho das notificações (Haiku sem ferramentas, sem memória: é só texto)."""
    linhas = "\n".join(f"- {n['quando']:%d/%m %H:%M} {n['app']}: {n['titulo']} — {n['texto'][:160]}"
                       for n in lista[:60])
    enxuto = ["--setting-sources", "", "--strict-mcp-config", "--disable-slash-commands",
              "--no-session-persistence", "--tools", ""]
    d = rodar_claude(PROMPT_NOTIFICACOES.format(lista=linhas), ["--model", "haiku", *enxuto],
                     timeout=120, sem_pensar=True)
    if d.get("is_error"):
        raise RuntimeError(d.get("result") or "erro do Claude")
    return re.sub(r"\*\*|`|^#+ *", "", d.get("result", ""), flags=re.M).strip()


def comentar_tela(area, modelo, recentes, lista, contexto, maldoso=False, tdah=False,
                  alvo="atividade", ponto=None, assuntos=(), eu=None, retrato="laranja", personalidade="claudinho"):
    """Tira print do monitor e pede um comentário ao Haiku. `alvo` diz do que a piada fala;
    com `ponto` (mouse ou Claudinho), manda também um zoom daquela região.
    Devolve (texto, assunto) ou None."""
    tela = ImageGrab.grab(bbox=area, all_screens=True)
    imagens, zoom = [], ""
    if ponto:
        px, py = ponto[0] - area[0], ponto[1] - area[1]
        caixa = (max(0, px - 450), max(0, py - 280), min(tela.width, px + 450), min(tela.height, py + 280))
        imagens.append(em_jpeg(tela.crop(caixa)))
        zoom = " A segunda imagem é um zoom, em tamanho real, da região do alvo."
    fator = tela.width / 1280 if tela.width > 1280 else 1
    img = tela.resize((1280, round(tela.height / fator))) if fator != 1 else tela
    imagens.insert(0, em_jpeg(img))

    def na_imagem(v, origem):
        return max(0, int((v - origem) / fator))

    descricao = "\n".join(
        f"- {j['exe']} \"{j['titulo'][:80]}\" em x={na_imagem(j['rect'][0], area[0])} "
        f"y={na_imagem(j['rect'][1], area[1])} até x={na_imagem(j['rect'][2], area[0])} "
        f"y={na_imagem(j['rect'][3], area[1])}" for j in lista[:8]) or "- nenhuma"
    onde_eu = f" por volta de x={na_imagem(eu[0], area[0])} y={na_imagem(eu[1], area[1])}" if eu else ""
    prompt = PROMPT_TELA.format(w=img.width, h=img.height, zoom=zoom, janelas=descricao, onde_eu=onde_eu, limites=LIMITES,
                                retrato=retrato,
                                contexto=contexto, alvo=ALVOS[alvo],
                                recentes="\n".join(f"- {r}" for r in recentes) or "- nenhuma ainda",
                                tom=tom_das_piadas(personalidade, maldoso),
                                estilo=ESTILO_TDAH if tdah else "", angulo=random.choice(ANGULOS),
                                assuntos="; ".join(assuntos) or "nenhum")
    mensagem = {"type": "user", "message": {"role": "user", "content": [
        *imagens, {"type": "text", "text": prompt}]}}
    # Claude Code no modo enxuto: sem plugins, hooks, MCP, skills e ferramentas. A demora vinha
    # disso (~5s por chamada) e de ler o print por ferramenta (uma ida e volta a mais), não do Haiku.
    enxuto = ["--setting-sources", "", "--strict-mcp-config", "--disable-slash-commands",
              "--no-session-persistence", "--tools", ""]
    d = rodar_claude(json.dumps(mensagem) + "\n", ["--model", modelo, *enxuto], timeout=180,
                     stream=True, sem_pensar=True)
    achado = re.search(r"\{.*\}", d.get("result", ""), re.S)
    if d.get("is_error") or not achado:
        return None
    try:
        r = json.loads(achado.group(0))
        return str(r["comentario"]).strip(), str(r.get("assunto", "")).strip().lower()
    except (ValueError, KeyError):
        # JSON torto (aspas dentro da piada, quebra de linha no haicai): pega o texto na marra
        bruto = re.search(r'"comentario"\s*:\s*"(.*)"\s*}', achado.group(0), re.S)
        assunto = re.search(r'"assunto"\s*:\s*"([^"]*)"', achado.group(0))
        if not bruto:
            return None
        return (re.sub(r"\s+", " ", bruto.group(1)).replace('\\"', '"').strip(),
                assunto.group(1).strip().lower() if assunto else "")


# ---------------- atalho global de teclado ----------------
MODIFICADORES = {"alt": 0x1, "ctrl": 0x2, "shift": 0x4, "win": 0x8}
TECLAS = {"space": 0x20, "espaco": 0x20, **{f"f{i}": 0x6F + i for i in range(1, 13)}}


def iniciar_atalho(texto, eventos, acao, ident=1):
    """Registra o atalho (ex.: "Win+Shift+Y") no Windows; quando apertado, manda ("menu", acao).
    `ident` separa um atalho do outro."""
    mods, vk = 0x4000, None  # 0x4000 = não repetir segurando a tecla
    for parte in texto.lower().replace(" ", "").split("+"):
        if parte in MODIFICADORES:
            mods |= MODIFICADORES[parte]
        elif parte in TECLAS:
            vk = TECLAS[parte]
        elif len(parte) == 1:
            vk = ord(parte.upper())
    if vk is None:
        return

    def laco():
        # o atalho pertence à thread que registrou: o laço de mensagens tem que ser aqui
        if not user32.RegisterHotKey(None, ident, mods, vk):
            eventos.put(("atalho_ocupado", texto))
            return
        msg = wt.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == 0x0312:  # WM_HOTKEY
                eventos.put(("menu", acao))

    threading.Thread(target=laco, daemon=True).start()


# ---------------- servidor de avisos ----------------
class ServidorUnico(ThreadingHTTPServer):
    # No Windows, reuse_address deixaria duas instâncias na mesma porta.
    allow_reuse_address = False
    allow_reuse_port = False
    daemon_threads = True


APP = None  # o Claudinho rodando (o painel lê o estado dele)
# a API do painel só responde com este token (vai embutido na página): outro site aberto no navegador
# não consegue mexer no Claudinho, porque não lê a página e não sabe o token
TOKEN = secrets.token_urlsafe(16)
def caminho_do_navegador():
    """Executável do navegador padrão (pelo comando "abrir" registrado pro tipo de link dele)."""
    try:
        chave = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, chave) as k:
            prog = winreg.QueryValueEx(k, "ProgId")[0]
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, prog + r"\shell\open\command") as k:
            comando = winreg.QueryValueEx(k, "")[0]
    except OSError:
        return None
    achado = re.match(r'\s*"([^"]+)"|\s*(\S+)', comando)
    return achado and (achado.group(1) or achado.group(2))


def chave_da_extensao():
    """Chave fixa da extensão do navegador (fica em ~/.claudinho/ext_token e vai embutida na extensão)."""
    arquivo = DADOS / "ext_token"
    try:
        return arquivo.read_text(encoding="utf-8").strip()
    except OSError:
        DADOS.mkdir(exist_ok=True)
        chave = secrets.token_urlsafe(24)
        arquivo.write_text(chave, encoding="utf-8")
        return chave


EXT_TOKEN = chave_da_extensao()
# o que a extensão sabe: quantas abas de cada site estão abertas e quando ela falou por último;
# `fila` = pedidos esperando ela buscar (somem em 8 s se ninguém pegar)
EXT = {"fila": [], "abas": {}, "visto": 0.0, "trava": threading.Lock()}


def versao_da_extensao():
    """Versão da cópia em ~/.claudinho/extensao (a que o navegador carrega). Se for mais nova que a rodando,
    a extensão se recarrega e passa a usar ela."""
    try:
        return json.loads((DADOS / "extensao" / "manifest.json").read_text(encoding="utf-8"))["version"]
    except Exception:
        return None


def montar_extensao():
    """Copia a extensão pra ~/.claudinho/extensao com a chave e o ícone (é essa pasta que o navegador carrega)."""
    destino = DADOS / "extensao"
    destino.mkdir(parents=True, exist_ok=True)
    for arquivo in (sistema.BASE / "extensao").iterdir():
        shutil.copy(arquivo, destino / arquivo.name)
    (destino / "config.js").write_text(
        f"self.CLAUDINHO = {json.dumps({'porta': PORTA, 'token': EXT_TOKEN})};\n", encoding="utf-8")
    desenhar_icone(128).save(destino / "icone.png")
    return destino


def extensao_conectada():
    return time.time() - EXT["visto"] < 5


PAGINAS = {"/painel": sistema.BASE / "painel.html", "/conversa": sistema.BASE / "conversa.html"}


def iniciar_servidor(eventos):
    class Receptor(BaseHTTPRequestHandler):
        def responder(self, codigo, corpo=b"", tipo="application/json"):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo + "; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def token_ok(self):
            return secrets.compare_digest(self.headers.get("X-Token", ""), TOKEN)

        def do_GET(self):
            pagina = PAGINAS.get(self.path.split("?")[0])
            if pagina:
                html = pagina.read_text(encoding="utf-8").replace("__TOKEN__", TOKEN)
                self.responder(200, html.encode("utf-8"), "text/html")
            elif self.path == "/api/estado" and self.token_ok() and APP:
                self.responder(200, json.dumps(APP.estado_painel(), ensure_ascii=False).encode("utf-8"))
            elif self.path == "/api/conversa" and self.token_ok() and APP:
                corpo = {"mensagens": APP.mem.historico(200), "pensando": APP.ocupado}
                self.responder(200, json.dumps(corpo, ensure_ascii=False).encode("utf-8"))
            else:
                self.responder(404)

        def do_POST(self):
            try:
                n = int(self.headers.get("Content-Length", 0))
                dados = json.loads(self.rfile.read(n) or b"{}")
                if self.path.startswith("/ext/"):  # extensão do navegador (e o musica.py pedindo pra ela)
                    if not secrets.compare_digest(self.headers.get("X-Claudinho-Ext", ""), EXT_TOKEN):
                        return self.responder(403)
                    with EXT["trava"]:
                        agora = time.time()
                        EXT["fila"] = [c for c in EXT["fila"] if agora - c["criado"] < 8]
                        if self.path == "/ext/buscar":
                            EXT["abas"], EXT["visto"] = dados.get("abas") or {}, agora
                            comandos, EXT["fila"] = EXT["fila"], []
                            # a versão dos arquivos que o Claudinho copiou: se mudou, a extensão se recarrega
                            corpo = {"comandos": comandos, "versao": versao_da_extensao()}
                            return self.responder(200, json.dumps(corpo).encode("utf-8"))
                        if self.path == "/ext/enviar":
                            site = dados.get("site")
                            comando = dados.get("comando") or {}
                            # "abrir" a extensão faz mesmo sem aba daquele site (ela cria uma); o resto precisa da aba
                            aberta = extensao_conectada() and (
                                (EXT["abas"].get(site) or 0) > 0 or comando.get("acao") == "abrir")
                            if aberta:
                                EXT["fila"].append(dict(comando, site=site, criado=agora))
                            return self.responder(200, json.dumps({"entregue": aberta}).encode("utf-8"))
                    return self.responder(404)
                if self.path.startswith("/api/"):
                    if not self.token_ok():
                        return self.responder(403)
                    if self.path == "/api/config":
                        eventos.put(("painel_cfg", dados["chave"], dados["valor"]))
                    elif self.path == "/api/acao":
                        eventos.put(("menu", str(dados["acao"])))
                    else:
                        return self.responder(404)
                else:  # o hook do Claude Code avisando que um chat terminou
                    eventos.put(("aviso", dados))
                self.responder(204)
            except Exception:
                self.responder(400)

        def log_message(self, *args):
            pass

    servidor = ServidorUnico(("127.0.0.1", PORTA), Receptor)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor


# ---------------- balão de fala ----------------
def paginar(texto, limite=420):
    """Quebra o texto em páginas de até ~`limite` caracteres, sem cortar palavras."""
    paginas, atual = [], ""
    for paragrafo in texto.split("\n"):
        for palavra in paragrafo.split(" "):
            if atual and len(atual) + len(palavra) + 1 > limite:
                paginas.append(atual.rstrip())
                atual = ""
            atual += palavra + " "
        atual = atual.rstrip(" ") + "\n"
    paginas.append(atual.strip())
    return [p for p in paginas if p] or [""]



class Balao:
    CAUDA_W, CAUDA_H = 22, 12

    def __init__(self, app, tipo, texto="", titulo=None, rodape=None, duracao=None, entrada=False,
                 botoes=None, botoes_no_hover=False):
        self.app, self.tipo, self.dados = app, tipo, None
        # texto grande vira páginas: clique passa para a próxima. (Rolagem não dá: no Windows a
        # rodinha só chega na janela com foco, e o sistema não deixa o balão pegar o foco.)
        self.paginas, self.pagina = paginar(texto), 0
        self.rodape_base = rodape or ""
        self.duracao = duracao
        self.ate = time.time() + duracao if duracao else None
        self.hover = False
        f = lambda tam, peso="normal": ctk.CTkFont("Segoe UI", tam, peso)

        # CTkToplevel (e não tk.Toplevel) para o ajuste de DPI entre monitores funcionar
        self.win = ctk.CTkToplevel(app.root, fg_color=CHAVE)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-transparentcolor", CHAVE)
        # nasce invisível: o CTk ainda redimensiona a janela (DPI) logo depois de criar,
        # e isso aparecia como uma tremida. Só mostra quando já está no tamanho e lugar certos.
        self.win.attributes("-alpha", 0.0)
        fora_da_barra(self.win)
        self.frame = ctk.CTkFrame(self.win, corner_radius=16, fg_color=FUNDO, bg_color=CHAVE,
                                  border_width=2, border_color=LARANJA)
        self.frame.pack(pady=(0, self.CAUDA_H))

        if entrada:  # conversa: nome dele e, do lado, o link pra abrir a conversa inteira numa janela maior
            topo = ctk.CTkFrame(self.frame, fg_color=FUNDO, height=18)
            topo.pack(fill="x", padx=(16, 42 if len(self.paginas) > 1 else 16), pady=(10, 0))
            ctk.CTkLabel(topo, text=titulo or "claudinho", font=f(12, "bold"), text_color=LARANJA,
                         anchor="w", height=18).pack(side="left")
            self.link(topo, "ver conversa", app.ver_conversa).pack(side="right")
        elif titulo:
            ctk.CTkLabel(self.frame, text=titulo, font=f(12, "bold"), text_color=LARANJA,
                         anchor="w", height=18).pack(fill="x", padx=16, pady=(10, 0))
        # conversa = última resposta (se tiver) + campo de texto embaixo, tudo no mesmo balão
        self.entry = None
        if texto or not entrada:
            tem_rodape = rodape is not None or len(self.paginas) > 1
            self.texto = ctk.CTkLabel(self.frame, text=self.paginas[0], wraplength=340, justify="left",
                                      anchor="w", text_color=TEXTO, font=f(13))
            margem_dir = 42 if len(self.paginas) > 1 else 16  # espaço pro ✕ no canto
            self.texto.pack(fill="x", padx=(16, margem_dir),
                            pady=(2 if titulo or entrada else 10, 2 if tem_rodape or entrada else 10))
        self.rodape = None
        if rodape is not None or len(self.paginas) > 1:
            self.rodape = ctk.CTkLabel(self.frame, text="", font=f(11), text_color=APAGADO,
                                       anchor="w", justify="left", height=16)
            self.rodape.pack(fill="x", padx=16, pady=(0, 2 if entrada else 10))
            self.desenhar_rodape()
        if entrada:
            # anexar um print da janela que você está usando à próxima mensagem
            # miniatura do print (só aparece com print anexado) + o link, na mesma linha
            linha_print = tk.Frame(self.frame, bg=FUNDO)
            linha_print.pack(fill="x", padx=16, pady=(4, 0))
            self.mini = tk.Label(linha_print, bg=FUNDO, bd=0, highlightthickness=1,
                                 highlightbackground=APAGADO, cursor="hand2")
            self.mini.bind("<Button-1>", lambda e: (app.alternar_print(), "break")[1])
            self.link_print = self.link(linha_print, "", app.alternar_print, anchor="w")
            self.link_print.pack(side="left", fill="x")
            self.mostrar_print(app.print_anexado)
            self.entry = ctk.CTkEntry(self.frame, width=340 if texto else 280, height=34, corner_radius=10,
                                      border_width=0, fg_color=FUNDO2, text_color=TEXTO,
                                      placeholder_text="responde aqui…" if texto else "pergunta pro claudinho…",
                                      placeholder_text_color=APAGADO, font=f(13))
            self.entry.pack(padx=10, pady=(4, 10))
        self.botoes = botoes or []
        self.linha_botoes = None
        self.botoes_no_hover = botoes_no_hover
        if self.botoes:  # ex.: confirmação "Pode" / "Não"; avaliação "boa" / "ruim"
            linha = self.linha_botoes = ctk.CTkFrame(self.frame, fg_color=FUNDO)
            if not botoes_no_hover:  # avaliação só aparece com o mouse em cima
                linha.pack(fill="x", padx=12, pady=(4, 12))
            for rotulo, acao, principal in reversed(self.botoes):
                ctk.CTkButton(linha, text=rotulo, width=84, height=30, corner_radius=10, font=f(12, "bold"),
                              fg_color=LARANJA if principal else FUNDO2, hover_color="#c4663f" if principal
                              else "#4a4945", text_color="white" if principal else TEXTO,
                              command=acao).pack(side="right", padx=(6, 0))

        self.cauda = tk.Canvas(self.win, width=self.CAUDA_W, height=self.CAUDA_H + 3, bg=CHAVE,
                               highlightthickness=0)
        w, h = self.CAUDA_W, self.CAUDA_H
        self.cauda.create_polygon(0, 0, w, 0, w // 2, h, fill=FUNDO, outline="")
        self.cauda.create_line(0, 0, w // 2, h, w, 0, fill=LARANJA, width=2)

        # mais de uma página: ✕ no canto pra fechar (clicar no texto só avança, em círculo)
        self.interagiu = False  # já mexeu nas páginas: aí não some sozinho e fecha com clique fora
        if len(self.paginas) > 1:
            fechar = tk.Label(self.frame, text="✕", bg=FUNDO, fg=APAGADO, font=("Segoe UI", 10),
                              cursor="hand2", padx=4)
            fechar.place(relx=1.0, x=-10, y=6, anchor="ne")
            fechar.bind("<Button-1>", lambda e: (self.fechar_pelo_x(), "break")[1])

        self.win.bind("<Enter>", self.mouse_entrou)
        self.win.bind("<Leave>", self.mouse_saiu)
        self.win.bind("<Button-1>", self.clicou)
        self.win.update_idletasks()
        self.posicionar()
        self.win.after(160, self.aparecer)

    def link(self, pai, texto, acao, **kw):
        """Textinho clicável (o clique não chega no balão, então não passa página)."""
        rotulo = tk.Label(pai, text=texto, bg=FUNDO, fg=APAGADO, font=("Segoe UI", 9, "underline"),
                          cursor="hand2", **kw)
        rotulo.bind("<Button-1>", lambda e: (acao(), "break")[1])
        rotulo.bind("<Enter>", lambda e: rotulo.configure(fg=LARANJA), add="+")
        rotulo.bind("<Leave>", lambda e: rotulo.configure(fg=APAGADO), add="+")
        return rotulo

    def mostrar_print(self, anexado):
        self.link_print.configure(text=f"print anexado ({anexado['nome']}) · tirar" if anexado
                                  else "📷 adicionar print da tela")
        if anexado and anexado.get("mini"):
            self.foto_mini = ImageTk.PhotoImage(anexado["mini"], master=self.win)  # guarda a referência
            self.mini.configure(image=self.foto_mini)
            self.mini.pack(side="left", padx=(0, 6), before=self.link_print)
        else:
            self.mini.pack_forget()

    def mouse_entrou(self, e):
        self.hover = True
        if self.botoes_no_hover and not self.linha_botoes.winfo_ismapped():
            self.linha_botoes.pack(fill="x", padx=12, pady=(4, 12))

    def mouse_saiu(self, e):
        self.hover = False
        if self.botoes_no_hover:
            # o Leave também dispara ao passar de um pedaço do balão pro outro: confere depois
            self.win.after(250, self.esconder_botoes_se_saiu)

    def esconder_botoes_se_saiu(self):
        try:
            x, y = self.win.winfo_pointerxy()
            dentro = self.win.winfo_containing(x, y)
            if dentro is None or dentro.winfo_toplevel() is not self.win:
                self.hover = False
                self.linha_botoes.pack_forget()
        except (tk.TclError, KeyError):
            pass

    def desenhar_rodape(self):
        partes = [self.rodape_base] if self.rodape_base else []
        if len(self.paginas) > 1:
            n, total = self.pagina + 1, len(self.paginas)
            partes.append(f"clique pra continuar ▸ {n}/{total}" if n < total
                          else f"clique pra voltar ao início ↺ {n}/{total}")
        self.rodape.configure(text="  ·  ".join(partes))

    def clicou(self, e):
        if self.entry is not None and str(e.widget).startswith(str(self.entry)):
            return  # clique no campo de texto: só digita
        if len(self.paginas) > 1:  # avança em círculo: da última volta pra primeira (fecha no ✕ ou clicando fora)
            self.pagina = (self.pagina + 1) % len(self.paginas)
            self.texto.configure(text=self.paginas[self.pagina])
            self.desenhar_rodape()
            self.interagiu = True
            self.ate = None  # está lendo: não some sozinho
        elif self.entry is None and not self.botoes:  # conversa e confirmação não fecham no clique
            self.app.fechar_balao()

    def fechar_pelo_x(self):
        if self.entry is not None:
            self.app.fechar_conversa()
        else:
            self.app.fechar_balao()

    def clique_fora(self, desde_a_ultima=False):
        """Botão do mouse apertado fora deste balão (e fora do mascote)? `desde_a_ultima` também conta
        um clique rápido que soltou entre duas olhadas."""
        if not (user32.GetAsyncKeyState(0x01) & (0x8001 if desde_a_ultima else 0x8000)):
            return False
        x, y = cursor()
        # clicar noutro balão dele (ex.: Pode/Não em cima da conversa) ou na janela da conversa não é "fora"
        nossas = [self.win] + [b.win for b in (self.app.balao, self.app.entrada) if b]
        for w in nossas:
            try:
                if w.winfo_exists() and w.winfo_rootx() <= x < w.winfo_rootx() + w.winfo_width() and \
                        w.winfo_rooty() <= y < w.winfo_rooty() + w.winfo_height():
                    return False
            except tk.TclError:
                pass
        return not self.app.mouse_no_mascote

    def aparecer(self):
        try:
            self.win.update_idletasks()
            self.posicionar()
            self.win.attributes("-alpha", 1.0)
        except tk.TclError:  # fechou antes de aparecer
            pass

    def expirou(self):
        if self.ate is None:
            return False
        if self.hover or self.app.mouse_no_mascote:  # mouse em cima: não some
            self.ate = max(self.ate, time.time() + 1.5)
        return time.time() > self.ate

    def mudar_rodape(self, texto):
        if self.rodape is not None and self.rodape_base != texto:
            self.rodape_base = texto
            self.desenhar_rodape()

    def mudar_texto(self, texto):
        self.texto.configure(text=texto)

    def posicionar(self):
        app = self.app
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        fh = self.frame.winfo_reqheight()
        cx = int(app.x) + app.W // 2
        _, (esq, topo, dir_, base), _ = monitor(cx, app.y + app.H // 2)
        x = limitar(cx - w // 2, esq + 6, dir_ - w - 6)
        y = int(app.y) - h + 2
        conversa = app.entrada if app.entrada is not self else None
        if conversa:  # a conversa está aberta: este balão (ex.: confirmação) empilha em cima dela, sem cobrir
            y = conversa.win.winfo_y() - fh - 4
            self.cauda.place_forget()
        elif y < topo + 6:  # sem espaço em cima: vai para baixo, sem cauda
            y = int(app.y) + app.H + 6
            self.cauda.place_forget()
        else:
            tx = limitar(cx - x - self.CAUDA_W // 2, 16, w - self.CAUDA_W - 16)
            self.cauda.place(x=tx, y=fh - 3)
        y = limitar(y, topo + 6, base - h - 6)
        # wm_* direto do tk (e não os do CTk): o CTk congela o tamanho antigo da janela ao ajustar
        # o DPI, inclusive travando min/max nele, e cortava o texto; aqui o tamanho segue o conteúdo.
        tk.Wm.wm_minsize(self.win, 1, 1)
        tk.Wm.wm_maxsize(self.win, 4000, 4000)
        tk.Wm.wm_geometry(self.win, f"{w}x{h}+{x}+{y}")

    def destruir(self):
        self.win.destroy()


class Gravador:
    """Faz de conta que é o canvas: só anota os retângulos do quadro (pra comparar com o anterior)."""

    def __init__(self):
        self.itens = []

    def delete(self, *_):
        self.itens = []

    def create_rectangle(self, x0, y0, x1, y1, fill, width=0):
        self.itens.append((x0, y0, x1, y1, fill))


# ---------------- o mascote ----------------
class Claudinho:
    def __init__(self, eventos):
        global APP
        APP = self  # o servidor local lê o estado pro painel
        self.eventos = eventos
        self.primeira_vez = not CONFIG.exists()  # nunca rodou neste PC (ou nesta pasta de dados)
        self.cfg = carregar_config()
        # piadas e notas, avisos do dia e conversa ficam no SQLite (memoria.py)
        self.mem = memoria.Memoria(DADOS / "claudinho.db")
        self.permissao = None  # pedido de confirmação esperando resposta
        self.print_anexado = None  # {"imagem": bloco, "nome": ...} que vai junto da próxima mensagem
        self.pergunta_atual = ""  # a última pergunta do chat (vira lembrança junto com a resposta)
        self.lendo_notificacoes = False
        self.falas_mostradas = deque(maxlen=6)  # (quando, texto) do que ele falou nos balões
        self.chat = ChatClaude(self.mem.meta("session_id"), self.cfg["pastas_leitura"], self.pedir_permissao,
                               lambda nome, entrada: self.eventos.put(("ferramenta", nome, entrada)),
                               self.cfg["personalidade"])
        threading.Thread(target=self.chat.aquecer, daemon=True).start()
        self.emoji, self.prox_emoji = None, time.time() + random.uniform(40, 90)  # reação flutuando
        self.esquete = None  # idle: deploy, café… (sai do mesmo timer das piadas)
        self.ultima_esquete = None
        # escolhida no painel ("Esquete agora"); CLAUDINHO_ESQUETE=inseto (por ex.) testa uma logo de cara
        self.esquete_forcada = os.environ.get("CLAUDINHO_ESQUETE")
        self.frente = -1  # lado pra onde está virado (franja, aba do boné… seguem)
        self.emo_ate, self.emo_musica = 0, None  # rock tocando: modo emo até essa hora
        self.musica = None  # o que está tocando, atualizado em segundo plano
        threading.Thread(target=self.acompanhar_musica, daemon=True).start()
        self.S = escala()
        self.falas = deque()       # o que ele tem para falar, em ordem
        self.balao = None          # balão de fala na tela
        self.entrada = None        # balão com o campo de pergunta
        self.ocupado = False       # pensando numa pergunta
        self.comentando = False    # olhando a tela em segundo plano
        self.olhando_forcado = False  # pediram "comentar agora": mostra que está olhando
        self.menu_aberto = False
        self.notebook = 0.0           # 0 = guardado, 1 = aberto e digitando (anima entre os dois)
        self.usou_ferramenta = False  # nesta pergunta ele já está fazendo coisas no PC
        self.pouso_ate = 0            # logo depois de ser solto: agachadinha
        self.app_atual, self.app_desde = "", time.time()
        self.t = 0

        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk(fg_color=CHAVE)
        self.root.title("Claudinho")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", CHAVE)
        fora_da_barra(self.root)
        self.W, self.H = (COLS + 2 * MARGEM) * self.S, (LINHAS + FOLGA) * self.S
        self.canvas = tk.Canvas(self.root, width=self.W, height=self.H, bg=CHAVE,
                                highlightthickness=0, cursor="hand2")
        self.canvas.pack()
        self.ultimo_quadro = None  # pra só redesenhar quando muda
        if self.primeira_vez:
            self.root.after(2500, self.boas_vindas)

        _, (esq, topo, dir_, base), _ = monitor(*cursor())
        self.x, self.y = float(dir_ - self.W - 120), float(base - self.H)
        self.modo, self.alvo, self.pausa_ate = "passeio", None, time.time() + 2
        self.movendo, self.dir_x, self.dir_y = False, -1, 0
        self.comentario_pendente = None
        self.cursor_fora_desde, self.monitor_destino = None, None
        self.prox_comentario = time.time() + 90
        self.piscar_ate, self.arrasto = 0, None

        self.canvas.bind("<ButtonPress-1>", self.apertou)
        self.canvas.bind("<B1-Motion>", self.arrastou)
        self.canvas.bind("<ButtonRelease-1>", self.soltou)
        self.canvas.bind("<Button-3>", self.menu)
        self.mouse_no_mascote = False
        self.canvas.bind("<Enter>", lambda e: setattr(self, "mouse_no_mascote", True))
        self.canvas.bind("<Leave>", lambda e: setattr(self, "mouse_no_mascote", False))
        self.visivel = True
        self.mover_janela()
        self.criar_icone_bandeja()
        iniciar_atalho(self.cfg["atalho_comentar"], self.eventos, "comentar_agora", 1)
        iniciar_atalho(self.cfg["atalho_venda"], self.eventos, "venda", 2)
        iniciar_atalho(self.cfg["atalho_resumir"], self.eventos, "resumir", 3)
        iniciar_atalho(self.cfg["atalho_notificacoes"], self.eventos, "notificacoes", 4)
        self.root.after(70, self.tick)

    # ---------- laço principal ----------
    def tick(self):
        try:
            self.t += 1
            self.processar_eventos()
            self.mover()
            self.cuidar_dos_baloes()
            self.talvez_comentar()
            self.talvez_emoji()
            self.cuidar_da_esquete()
            self.animar_emoji()
            self.desenhar_se_mudou()
            if self.t % 100 == 0:
                self.chat.dormir_se_parado()
        finally:
            # parado à toa (sem andar, falar, esquete…), o laço anda mais devagar: gasta menos processador
            self.root.after(150 if self.a_toa() else 70, self.tick)

    def a_toa(self):
        return not (self.movendo or self.balao or self.entrada or self.esquete or self.emoji or self.arrasto
                    or self.ocupado or self.olhando_forcado or self.lendo_notificacoes or self.notebook > 0
                    or self.modo != "passeio" or time.time() < self.pouso_ate)

    def desenhar_se_mudou(self):
        """Monta o quadro numa lista e só mexe no canvas (a parte cara) se ele for diferente do anterior:
        parado, olhando pro mesmo lado, o quadro se repete e não custa nada."""
        tela, self.canvas = self.canvas, Gravador()
        try:
            self.desenhar()
        finally:
            quadro, self.canvas = self.canvas.itens, tela
        if quadro != self.ultimo_quadro:
            tela.delete("all")
            for x0, y0, x1, y1, cor in quadro:
                tela.create_rectangle(x0, y0, x1, y1, fill=cor, width=0)
            self.ultimo_quadro = quadro

    def mover_janela(self):
        self.root.geometry(f"{self.W}x{self.H}+{int(self.x)}+{int(self.y)}")

    def centro(self):
        return self.x + self.W / 2, self.y + self.H / 2

    def area(self):
        return monitor(*self.centro())

    def limitar_na_area(self, x, y, area):
        esq, topo, dir_, base = area
        return limitar(x, esq, dir_ - self.W), limitar(y, topo, base - self.H)

    # ---------- movimento ----------
    def mover(self):
        self.movendo = False
        if self.arrasto or self.menu_aberto:
            return
        agora = time.time()
        id_aqui, area, _ = self.area()

        if self.cfg["seguir_mouse_entre_monitores"]:
            cx, cy = cursor()
            id_mouse, area_mouse, _ = monitor(cx, cy)
            if self.modo == "correndo" and id_mouse != self.monitor_destino:
                # o mouse mudou de ideia no meio da corrida
                self.cursor_fora_desde = None
                if id_mouse == id_aqui:  # voltou para onde ele está: desiste da corrida
                    self.modo, self.alvo = "passeio", None
                    self.pausa_ate = agora + random.uniform(1, 3)
                    return
                self.correr_para(cx, cy, id_mouse, area_mouse)
            elif id_mouse != id_aqui and self.modo != "correndo":
                if self.cursor_fora_desde is None:
                    self.cursor_fora_desde = agora
                elif agora - self.cursor_fora_desde > 0.7:
                    self.correr_para(cx, cy, id_mouse, area_mouse)
            else:
                self.cursor_fora_desde = None

        if self.modo == "passeio":
            # parado quando fala, e também quando está trabalhando no notebook
            falando = (self.balao and self.balao.tipo != "pensando") or self.entrada or self.ocupado \
                or (self.esquete and not self.anda_na_esquete())  # caçando o bug / montando o robô: anda
            if falando:
                return
            if self.alvo is None:
                # numa esquete que anda (robô, bug), quem escolhe o destino é a esquete: nada de passear por aí
                if agora < self.pausa_ate or self.anda_na_esquete():
                    return
                self.alvo = self.novo_alvo(area)

        vel = self.S * 2.6 if self.modo == "correndo" or self.anda_na_esquete() else max(2, self.S * 0.45)
        dx, dy = self.alvo[0] - self.x, self.alvo[1] - self.y
        dist = (dx * dx + dy * dy) ** 0.5
        if abs(dx) > 1:
            self.dir_x = 1 if dx > 0 else -1
        self.dir_y = (1 if dy > 0 else -1) if abs(dy) > abs(dx) * 0.6 and abs(dy) > 1 else 0
        if dist <= vel:
            self.x, self.y = self.alvo
            self.chegou()
        else:
            self.x += vel * dx / dist
            self.y += vel * dy / dist
            self.movendo = True
        self.mover_janela()

    def correr_para(self, cx, cy, id_monitor, area):
        if self.cfg["movimento"] == "horizontal":
            destino = (cx - self.W / 2, area[3] - self.H)
        else:
            destino = (cx - self.W / 2, cy + 30)
        self.modo, self.alvo = "correndo", self.limitar_na_area(*destino, area)
        self.monitor_destino = id_monitor
        self.comentario_pendente = None

    def novo_alvo(self, area):
        esq, topo, dir_, base = area
        if self.cfg["movimento"] == "horizontal":
            return self.limitar_na_area(random.uniform(esq, dir_ - self.W), self.y, area)
        cx, cy = cursor()
        if random.random() < 0.3 and monitor(cx, cy)[2] == monitor(*self.centro())[2]:
            # curioso: vai dar uma olhada perto do mouse
            return self.limitar_na_area(cx + random.uniform(-180, 180), cy + random.uniform(40, 140), area)
        return self.limitar_na_area(random.uniform(esq, dir_ - self.W),
                                    random.uniform(topo, base - self.H), area)

    def chegou(self):
        if self.modo == "comentar" and self.comentario_pendente:
            self.comentar(self.comentario_pendente)
        self.comentario_pendente = None
        self.modo, self.alvo = "passeio", None
        self.pausa_ate = time.time() + random.uniform(1.5, 6)

    # ---------- desenho ----------
    def desenhar(self):
        c, S = self.canvas, self.S
        c.delete("all")
        visual = self.cfg["visual"]
        corpo = skins.cor_do_corpo(visual["cor"], self.t)
        olho = skins.CORES[visual["cor"]]["olho"]
        correndo = self.movendo and (self.modo == "correndo" or self.anda_na_esquete())
        carregado = bool(self.arrasto and self.arrasto["moveu"])  # sendo levado pelo mouse
        pousando = time.time() < self.pouso_ate
        if pousando:
            pulo = -1  # agachadinha: afunda uma linha, as perninhas "dobram"
        elif self.balao and self.balao.tipo == "aviso":
            pulo = FOLGA if self.t % 4 < 2 else 0
        elif correndo:
            pulo = self.t % 2
        else:
            pulo = 0
        esq = self.esquete["nome"] if self.esquete and not carregado else None
        fase = (time.time() - self.esquete["inicio"]) / esquetes.ESQUETES[esq]["duracao"] if esq else 0
        m = self.musica
        emo = (time.time() < self.emo_ate and m and m["tocando"]
               and (m["titulo"], m["artista"]) == self.emo_musica and not carregado)
        if emo and not self.movendo and not esq and pulo == 0:  # headbang: abaixa a cabeça no ritmo
            pulo = -1 if (self.t // 2) % 4 == 0 else 0
        metal = virada_ultron(fase, self.t) if esq == "ultron" else 0.0  # 0 = ele mesmo, 1 = metal
        if metal == 1.0:
            pulo = 1 if (self.t // 8) % 2 else 0  # flutuando, ameaçador
        comendo = esq == "inseto" and self.esquete.get("fase_inseto") == "comendo"
        if comendo:  # nhac nhac: amassadinha rápida
            pulo = -1 if self.t % 3 else 0
        elif esq == "cochilo":  # respirando devagar
            pulo = -1 if (self.t // 14) % 2 else 0
        elif esq == "danca":
            pulo = 1 if self.t % 6 < 3 else 0
        elif esq == "construindo" and (self.depois_do_flagra() or 99) < 0.4:  # levou um susto: você estava olhando!
            pulo = 1
        elif esq == "build_quebrou":  # encolhido debaixo da chuva
            pulo = -1
        elif esq == "fogo" and fase < 0.6:  # pulando de desespero
            pulo = self.t % 2
        oy = (FOLGA - pulo) * S

        def px(col, lin, cor):
            x0 = (col + MARGEM) * S
            c.create_rectangle(x0, oy + lin * S, x0 + S, oy + (lin + 1) * S, fill=cor, width=0)

        if metal:  # momento Ultron: o corpo vai pro metal e os olhos pro vermelho (brilhando quando completo)
            corpo = misturar(corpo, skins.CORES["metal"]["corpo"], metal)
            olho = misturar(olho, "#ff6b5e" if metal == 1.0 and self.t % 10 < 3 else "#ff3b30", metal)

        # notebook: abre aos poucos quando começa a trabalhar e fecha quando termina (transição)
        nb = esquetes.ESQUETES[esq].get("notebook") if esq else None  # True ou (de, até) na esquete
        no_notebook = self.ocupado or (nb is True and fase < 0.9) or (isinstance(nb, tuple) and nb[0] <= fase < nb[1])
        alvo_nb = 1.0 if no_notebook and not self.movendo else 0.0
        self.notebook += max(-0.15, min(0.15, alvo_nb - self.notebook))
        digitando = self.notebook >= 0.99
        trabalho = self.esquete.get("acao") if esq == "construindo" and self.esquete.get("montando") else None
        martelando = bool(trabalho) and not self.movendo
        bracos_soltos = digitando or carregado or martelando or esq in ("alongar", "danca", "fogo", "jogo", "malhando")

        for lin, linha in enumerate(CORPO):
            for col, ch in enumerate(linha):
                if ch == "X" and not (bracos_soltos and col in (0, 10)):  # bracinhos saem do lugar
                    px(col, lin, corpo)
        if esq == "alongar":  # bracinhos sobem devagar, ficam lá em cima e descem
            linhas = (-2, -1) if 0.15 < fase < 0.75 else ((0, 1) if 0.05 < fase < 0.9 else (3, 4))
            for col in (0, 10):
                for lin in linhas:
                    px(col, lin, corpo)
        elif esq == "danca":  # um bracinho em cima, o outro embaixo, trocando no ritmo
            for col, cima in ((0, self.t % 6 < 3), (10, self.t % 6 >= 3)):
                px(col, -1 if cima else 4, corpo)
                px(col, 0 if cima else 5, corpo)
        elif esq == "fogo":  # desespero (bracinhos pra cima, rápido); depois segura o balde do lado do fogo
            if fase < 0.6:
                for col in (0, 10):
                    cima = (self.t + col) % 2 == 0
                    px(col, -1 if cima else 0, corpo)
                    px(col, 0 if cima else 1, corpo)
            else:
                for col, lin in ((0, 2), (0, 3), (10, 3), (10, 4)):
                    px(col, lin, corpo)
        elif esq == "jogo":  # apertando os botões do controle feito louco
            for col, sobe in ((0, self.t % 2 == 0), (10, self.t % 2 == 1)):
                px(col, 4 if sobe else 5, corpo)
                px(col, 5 if sobe else 6, corpo)
        elif martelando:  # braço esticado pro lado do robô, com a ferramenta da vez na mão
            lado = 1 if self.esquete["robo"]["x"] > self.x else -1
            mao = 10 if lado == 1 else 0
            outra = 0 if mao == 10 else 10
            px(outra, 3, corpo)
            px(outra, 4, corpo)
            if trabalho == "martelo":  # levanta o martelo… e PÁ
                if (self.t // 3) % 2 == 0:
                    px(mao, 3, corpo)
                    px(mao + lado, 2, corpo)  # braço pra cima e pra fora
                    px(mao + lado, 1, CABO)
                    px(mao + lado, 0, PESO)  # cabeça do martelo lá em cima
                    px(mao + 2 * lado, 0, PESO)
                else:
                    px(mao, 4, corpo)
                    px(mao + lado, 4, corpo)  # braço esticado batendo
                    px(mao + 2 * lado, 4, CABO)
                    px(mao + 3 * lado, 3, PESO)
                    px(mao + 3 * lado, 4, PESO)
                    px(mao + 3 * lado, 5, PESO)
            elif trabalho == "solda":  # maçarico firme, ponta piscando
                px(mao, 4, corpo)
                px(mao + lado, 4, corpo)
                px(mao + 2 * lado, 4, PESO)
                px(mao + 3 * lado, 4, "#bfe6ff" if self.t % 2 else "#ffffff")
            else:  # parafuso: chave de fenda girando (o cabo pisca entre as cores)
                px(mao, 4, corpo)
                px(mao + lado, 4, corpo)
                px(mao + 2 * lado, 4, PALHA if (self.t // 2) % 2 else "#c0392b")
                px(mao + 3 * lado, 4, BARRA)
        elif esq == "malhando":  # um braço levanta o halter, depois o outro
            erguido = 0 if (self.t // 12) % 2 == 0 else 10
            for col in (0, 10):
                for lin in ((-1, 0) if col == erguido else (3, 4)):
                    px(col, lin, corpo)
        if carregado:  # bracinhos pra cima, sacudindo ("uiii!")
            for col in (0, 10):
                topo = 1 if (self.t + col) % 4 < 2 else 2
                px(col, topo, corpo)
                px(col, topo + 1, corpo)
        if digitando:  # bracinhos batendo no teclado, um de cada vez
            for col, sobe in ((0, self.t % 2 == 0), (10, self.t % 2 == 1)):
                px(col, 3 if sobe else 4, corpo)
                px(col, 4 if sobe else 5, corpo)

        if self.movendo:
            olhar_x, olhar_y = self.dir_x, self.dir_y
        else:  # parado, fica olhando para o mouse
            mx, my = cursor()
            cx, cy = self.centro()
            olhar_x = 0 if abs(mx - cx) < self.W else (1 if mx > cx else -1)
            olhar_y = 0 if abs(my - cy) < self.H else (1 if my > cy else -1)
        pensando = self.olhando_forcado and not self.ocupado  # Win+Y: olhando a tela e pensando
        if esq and fase < esquetes.ESQUETES[esq].get("pensa_ate", 0):  # "tive uma ideia": pensa antes de trabalhar
            pensando = True
        if pensando and not self.movendo:  # pensando: olhinhos pra cima, de lado
            olhar_x, olhar_y = 1, -1
        if self.notebook > 0.5:  # no notebook: olhando pra tela dele
            olhar_x, olhar_y = 0, 1
        if esq == "danca":
            olhar_x, olhar_y = (-1 if self.t % 12 < 6 else 1), 0
        elif esq == "cafe":
            olhar_x, olhar_y = 1, 0  # olhando pra caneca
        elif esq == "construindo":  # de olho no robô → olha pra você (flagra) → olha pro robô sumindo → disfarça
            lado_robo = 1 if self.esquete["robo"]["x"] > self.x else -1
            dt = self.depois_do_flagra()
            olhar_x, olhar_y = ((lado_robo, 0) if dt is None else (0, 0) if dt < FLAGRA_SUSTO
                                else (lado_robo, 0) if dt < FLAGRA_PUF else (-lado_robo, -1))
        elif esq in OLHAR_ESQUETE:
            olhar_x, olhar_y = OLHAR_ESQUETE[esq](fase, self.t)
        piscando = time.time() < self.piscar_ate
        # cochilando, se espreguiçando ou no gole do café: olhinho fechado (só a linha de baixo)
        gole = esq == "cafe" and (time.time() - self.esquete["inicio"]) % 3 < 1.1
        if esq == "inseto" and self.esquete.get("inseto") and not self.movendo:  # de olho no bicho
            olhar_x, olhar_y = (1 if self.esquete["inseto"]["x"] > self.x else -1), 1
        mordida = esq == "pizza" and (time.time() - self.esquete["inicio"]) % 2.5 < 0.8
        tedio = esq == "reuniao" and (self.t // 6) % 5 != 0  # reunião: olho quase sempre fechado
        if esq == "cochilo" or (esq == "alongar" and 0.15 < fase < 0.75) or gole or comendo or mordida or tedio:
            piscando = True
        if olhar_x:  # o lado pra onde ele está virado (olhando pro meio, fica o último): adereços seguem
            self.frente = olhar_x
        l1, l2 = OLHOS_Y[olhar_y]
        if self.cfg["vendado"]:  # faixa nos olhos, com o nó balançando atrás da cabeça
            for col in range(1, 10):
                px(col, 1, VENDA)
                px(col, 2, VENDA)
            px(5, 1, VENDA_BRILHO)  # dobrinha do pano
            # nó atrás da cabeça: duas pontinhas que abrem e fecham com o vento
            px(10, 1, VENDA)
            px(10, 2, VENDA)
            abertas = (self.t // 3) % 2
            px(11, 1 - abertas, VENDA)
            px(11, 2 + abertas, VENDA)
        elif carregado:  # olhos arregalados, sem piscar
            for col in OLHOS_X[0]:
                for lin in (0, 1, 2):
                    px(col, lin, olho)
        else:
            for col in OLHOS_X[olhar_x]:
                if not piscando:
                    px(col, l1, olho)
                px(col, l2, olho)

        # skin: adereços em camadas; tocando rock, o pacote emo vai por cima do que estiver escolhido
        vestido = dict(visual, **skins.PACOTES["emo"]["aderecos"]) if emo else visual
        sem = set()
        if self.cfg["vendado"]:
            sem.add("olhos")  # a venda ganha dos óculos
        if esq in ("reuniao", "build_quebrou"):
            sem.add("cabeca")  # o fone da reunião / a nuvem ocupam a cabeça
        if bracos_soltos:
            sem.add("bracos")  # munhequeira e cia só com os bracinhos no lugar
        for espaco in ("rosto", "pescoco", "olhos", "cabeca", "bracos"):
            if vestido.get(espaco) and espaco not in sem:
                for col, lin, cor in skins.pixels(vestido[espaco], self.t, self.frente, (olhar_x, olhar_y)):
                    px(col, lin, cor)

        if carregado:  # perninhas penduradas, balançando pro lado contrário do movimento e chutando
            vx = self.arrasto.get("vx", 0)
            lado = 0 if abs(vx) < 2 else (-1 if vx > 0 else 1)
            for i, col in enumerate(PERNAS):
                px(col, 6, corpo)
                if (i + self.t // 2) % 2 == 0:
                    px(col + lado, 7, corpo)
        else:
            passo = self.t if correndo else self.t // 2
            for i, col in enumerate(PERNAS):
                px(col, 6, corpo)
                if not (self.movendo and i % 2 == passo % 2):
                    px(col, 7, corpo)

        if correndo:  # poeirinha atrás
            atras = -1 - (self.t % 2) if self.dir_x > 0 else COLS + (self.t % 2)
            px(atras, 7, POEIRA)
            px(atras - self.dir_x * 1, 6 - self.t % 2, POEIRA)

        if self.notebook > 0:  # base do notebook na frente; a tampa sobe conforme abre
            for col in range(1, 10):
                px(col, 6, NB_BASE)
            altura = round(self.notebook * 3)
            for lin in range(6 - altura, 6):
                for col in range(2, 9):
                    px(col, lin, NB_TAMPA)
            if altura == 3:
                px(5, 4, corpo)  # logo na tampa
                if digitando:  # teclinha piscando na base
                    tecla = (MARGEM + 1 + random.randrange(9)) * S
                    c.create_rectangle(tecla + S // 4, oy + 6 * S + S // 4, tecla + 3 * S // 4,
                                       oy + 6 * S + S // 2, fill=NB_TECLA, width=0)

        if pensando:  # bolinhas de pensamento subindo da cabeça, uma de cada vez
            meio = S // 2
            for n, (col, lin) in enumerate([(10, -0.6), (11, -1.3), (12, -2.0)]):
                if (self.t // 4) % 4 > n:
                    x0, y0 = (col + MARGEM) * S, oy + lin * S
                    lado = meio + n * 2
                    c.create_rectangle(x0, y0, x0 + lado, y0 + lado, fill=POEIRA, width=0)

        if esq:
            self.desenhar_esquete(esq, fase, oy)

        if random.random() < 0.012:
            self.piscar_ate = time.time() + 0.18

    def desenhar_esquete(self, esq, fase, oy):
        """Os acessórios das esquetes: caneca com fumaça, zzz, gota de suor, notinhas."""
        c, S, t = self.canvas, self.S, self.t

        def quadrado(col, lin, cor, lado=1.0):
            x0, y0 = (col + MARGEM) * S, oy + lin * S
            c.create_rectangle(x0, y0, x0 + lado * S, y0 + lado * S, fill=cor, width=0)

        if esq == "cafe":
            topo = 2 if (time.time() - self.esquete["inicio"]) % 3 < 1.1 else 3  # gole: levanta a caneca
            for col in (11, 12):
                quadrado(col, topo, CAFE)
                quadrado(col, topo + 1, CANECA)
                quadrado(col, topo + 2, CANECA)
            quadrado(13, topo + 1, CANECA, 0.6)  # alça
            if topo == 3:  # fumacinha subindo e balançando
                for k in range(2):
                    quadrado(11.2 + ((t // 4 + k) % 2) * 0.8, 1.6 - k * 0.9, POEIRA, 0.45)
        elif esq == "cochilo":  # zzz subindo em diagonal, cada um maior
            for k in range(3):
                p = (t / 6 + k * 3) % 9
                lado = 0.35 + p * 0.06
                quadrado(10.5 + p * 0.3, 0.2 - p * 0.25, POEIRA, lado)
        elif esq == "push_force" and fase > 0.3:  # gotinha de suor escorrendo da cabeça
            quadrado(10.6, -0.4 + (t // 3 % 4) * 0.45, SUOR, 0.5)
        elif esq == "danca":  # notinha subindo do lado
            sobe = (t // 3) % 4 * 0.4
            quadrado(11.5, 0.6 - sobe, NB_TECLA, 0.6)  # bolinha da nota
            quadrado(12.0, -0.4 - sobe, NB_TECLA, 0.25)  # haste
            quadrado(12.0, -0.15 - sobe, NB_TECLA, 0.25)
        elif esq == "build_quebrou":  # nuvenzinha em cima da cabeça e chuva caindo nele
            for col in range(3, 8):
                quadrado(col, -2, NUVEM)
            for col in range(2, 9):
                quadrado(col, -1, NUVEM)
            for k in range(4):
                quadrado(2.5 + k * 1.7, -0.1 + ((t + k * 3) % 6) * 0.8, SUOR, 0.3)
        elif esq == "fogo":  # foguinho do lado esquerdo; o balde de água apaga; sobra fumaça
            if fase < 0.85:
                for col in (-3, -2, -1):
                    quadrado(col, 7, FOGO_1)
                    quadrado(col, 6, FOGO_2)
                quadrado(-3 + (t // 2) % 2, 5, FOGO_3)
                quadrado(-2, 5, FOGO_2)
                if t % 4 < 2:
                    quadrado(-2, 4, FOGO_3)
                if fase > 0.6:  # água caindo do balde
                    for k in range(3):
                        quadrado(-2.8 + k * 0.9, 3 + ((t + k) % 4) * 0.8, SUOR, 0.4)
                    quadrado(-1.5, 1.5, BALDE)  # balde na mão
                    quadrado(-0.5, 1.5, BALDE, 0.5)
            else:
                for k in range(3):
                    quadrado(-2.2 + (k % 2) * 0.5, 6 - k * 1.3 - (t % 4) * 0.3, POEIRA, 0.5)
        elif esq == "pato" and fase < 0.93:  # patinho de borracha à esquerda + "…" dele falando
            for col in (-3, -2, -1):
                quadrado(col, 6, PATO)
            quadrado(-2, 5, PATO)
            quadrado(-1, 5, PATO)
            quadrado(-2, 4, PATO)
            quadrado(-2.6, 4.4, BICO, 0.6)
            quadrado(-1.85, 4.25, OLHO, 0.3)
            if fase < 0.85:
                for k in range((t // 4) % 4):
                    quadrado(-1 + k * 0.6, 1.8, NB_TECLA, 0.35)
        elif esq == "npm":  # caixa que cresce (largura até 3, altura até 5)
            larg, alt = 1 + round(fase * 2), 1 + round(fase * 4)
            for col in range(-larg, 0):
                for lin in range(8 - alt, 8):
                    quadrado(col, lin, CAIXA)
            meio = -larg / 2 - 0.2
            for lin in range(8 - alt, 8):
                quadrado(meio, lin, FITA, 0.4)
        elif esq == "pizza":  # fatia na mão direita; cada mordida tira um pedaço (a ponta primeiro)
            fatia = [(11, 4, QUEIJO), (11, 3, QUEIJO), (12, 3, PEPPERONI), (11, 2, BORDA), (12, 2, BORDA)]
            for col, lin, cor in fatia[min(4, int(fase * 4.5)):]:
                quadrado(col, lin, cor)
        elif esq == "jogo":  # controle na frente, botões piscando
            for col in range(3, 8):
                quadrado(col, 4.6, CONTROLE)
            quadrado(3, 5.6, CONTROLE)
            quadrado(7, 5.6, CONTROLE)
            quadrado(3.4, 4.85, NB_TECLA, 0.4)  # direcional
            quadrado(6.1, 4.8, PEPPERONI if t % 2 else CONTROLE, 0.35)
            quadrado(6.6, 5.1, VERDE if t % 3 else CONTROLE, 0.35)
        elif esq == "limpeza":  # vassourinha balançando e a poeira indo embora
            vai = 0.5 * ((t // 4) % 2)
            for k in range(5):
                quadrado(11 + k * 0.25 + vai, 1 + k, CABO, 0.4)
            quadrado(11.3 + vai, 6, PALHA)
            quadrado(12.3 + vai, 6, PALHA, 0.7)
            for k in range(3):
                quadrado(12 + (t / 2 + k * 2) % 4, 7.2, POEIRA, 0.4)
        elif esq == "reuniao":  # fone com microfone
            for col in range(1, 10):
                quadrado(col, -1, FONE)
            for col in (0, 10):
                quadrado(col, 0, FONE)
                quadrado(col, 1, FONE)
            quadrado(10.5, 2.1, FONE, 0.4)
            quadrado(10.1, 2.5, FONE, 0.4)
        elif esq == "borboleta":  # a joaninha com asas sobe voando em diagonal
            col, lin = -2 + fase * 14, 6 - fase * 8 + math.sin(fase * 20) * 0.6
            asa = -0.5 if t % 2 else 0.3
            quadrado(col - 0.5, lin + asa, NB_TECLA, 0.5)
            quadrado(col + 0.6, lin + asa, NB_TECLA, 0.5)
            quadrado(col, lin, esquetes.CORES_INSETO["R"], 0.6)
        elif esq == "construindo":
            self.desenhar_projeto_secreto(fase, quadrado)
        elif esq == "malhando":  # halter em cima do braço erguido; suor no fim
            erguido = 0 if (t // 12) % 2 == 0 else 10
            quadrado(erguido - 1, -2, PESO)
            quadrado(erguido, -1.8, BARRA, 0.6)
            quadrado(erguido + 1, -2, PESO)
            if fase > 0.5:
                quadrado(10.6, -0.4 + (t // 3 % 4) * 0.45, SUOR, 0.5)

    # ---------- mouse ----------
    def apertou(self, e):
        self.arrasto = {"dx": e.x_root - self.x, "dy": e.y_root - self.y,
                        "x0": e.x_root, "y0": e.y_root, "moveu": False}

    def arrastou(self, e):
        a = self.arrasto
        if not a:
            return
        if abs(e.x_root - a["x0"]) + abs(e.y_root - a["y0"]) > 5:
            a["moveu"] = True
        if a["moveu"]:
            novo_x = e.x_root - a["dx"]
            a["vx"] = a.get("vx", 0) * 0.6 + (novo_x - self.x) * 0.4  # pra onde as perninhas balançam
            self.x, self.y = novo_x, e.y_root - a["dy"]
            self.mover_janela()
            self.reposicionar_baloes()

    def soltou(self, e):
        moveu = self.arrasto and self.arrasto["moveu"]
        if moveu:
            self.pouso_ate = time.time() + 0.35  # agachadinha ao ser colocado no chão
        self.arrasto = None
        if moveu:
            self.modo, self.alvo, self.comentario_pendente = "passeio", None, None
            self.pausa_ate = time.time() + 2
        else:
            self.alternar_entrada()

    # ---------- menus (botão direito no mascote e ícone na bandeja) ----------
    # ---------- música ----------
    def atualizar_musica(self):
        self.musica = musica.tocando() if self.cfg["ver_musica"] else None
        try:
            self.icone.update_menu()
        except Exception:
            pass

    def e_rock(self, m):
        """A música é rock? Guarda a resposta por artista no banco: o Haiku só é chamado pra artista novo."""
        if not self.cfg["emo_rock"] or not m.get("artista") or not tem_claude():
            return False
        generos = self.mem.meta("artistas_rock", {})
        artista = m["artista"].strip().lower()
        if artista not in generos:
            try:
                generos[artista] = artista_de_rock(m["artista"], m["titulo"])
            except Exception:
                return False  # sem resposta: não guarda, tenta de novo na próxima
            self.mem.guardar_meta("artistas_rock", generos)
        return generos[artista]

    def acompanhar_musica(self):
        anterior = None
        while True:
            self.atualizar_musica()
            m = self.musica
            chave = m and (m["titulo"], m["artista"])
            if m and m["tocando"] and anterior is not None and chave != anterior:
                m["rock"] = self.e_rock(m)
                self.eventos.put(("musica_nova", m))  # começou outra música
            if m:
                anterior = chave
            time.sleep(10)

    def talvez_comentar_musica(self, m):
        """Música nova: às vezes ele comenta (curiosidade ou cantarola), com a notinha 🎵.
        Em maldoso/TDAH bem menos, que nesses modos a zoeira é sobre a tela."""
        so_tela = self.cfg["modo_maldoso"] or self.cfg["modo_tdah"]
        if (not self.cfg["comentar_tela"] or self.comentando or self.ocupado or self.balao or self.entrada
                or not tem_claude() or random.random() > (0.15 if so_tela else 0.45)):
            return
        self.comentando = True
        maldoso, recentes = self.cfg["modo_maldoso"], self.mem.piadas_recentes(8)

        def trabalho():
            try:
                r = comentar_musica(m, maldoso, recentes, self.cfg["personalidade"])
            except Exception:
                r = None
            self.eventos.put(("comentario_musica", r))

        threading.Thread(target=trabalho, daemon=True).start()

    def tocar_no_youtube_music(self, termo):
        """Busca e toca no YouTube Music (em thread: a busca leva ~2 s) e conta o que achou."""
        def trabalho():
            try:
                m = musica.tocar_no_youtube_music(termo)
            except Exception:
                m = None
            self.eventos.put(("musica_pedida", termo, m))  # a fila de falas é do laço principal
        threading.Thread(target=trabalho, daemon=True).start()

    def itens_musica(self):
        m = self.musica if self.cfg["ver_musica"] else None
        if not m:
            return []
        nome = f"{m['titulo']} - {m['artista']}" if m["artista"] else m["titulo"]
        if len(nome) > 45:
            nome = nome[:44] + "…"
        return [(f"🎵 {nome}", "musica:alternar", None),
                ("⏸ Pausar" if m["tocando"] else "▶ Tocar", "musica:alternar", None),
                ("⏭ Próxima", "musica:proxima", None),
                ("⏮ Anterior", "musica:anterior", None),
                None]

    def itens_menu(self):
        """(rótulo, ação, marcado?) — None = separador. Usado pelos dois menus.
        Só o do dia a dia (e o que tem atalho); configuração e skins ficam no painel."""
        return [
            ("Perguntar", "perguntar", None),
            ("Esconder o Claudinho" if self.visivel else "Mostrar o Claudinho", "visivel", None),
            None,
            *self.itens_musica(),
            (f"Comentar a tela agora ({self.cfg['atalho_comentar']})", "comentar_agora", None),
            (f"Resumir/explicar a janela ({self.cfg['atalho_resumir']})", "resumir", None),
            (f"Resumir minhas notificações 🔔 ({self.cfg['atalho_notificacoes']})", "notificacoes", None),
            (f"Faixa nos olhos 🙈 ({self.cfg['atalho_venda']})", "venda", lambda: self.cfg["vendado"]),
            None,
            ("Configurações e skins ⚙️", "painel", None),
            ("Sair", "sair", None),
        ]

    def menu(self, e):
        self.vars_menu = []  # guarda as variáveis: sem referência o tk perde a marquinha ✓

        def montar(m, itens):
            for item in itens:
                if item is None:
                    m.add_separator()
                elif isinstance(item[1], list):
                    sub = tk.Menu(m, tearoff=0)
                    montar(sub, item[1])
                    m.add_cascade(label=item[0], menu=sub)
                elif item[2]:
                    var = tk.BooleanVar(m, value=item[2]())
                    self.vars_menu.append(var)
                    m.add_checkbutton(label=item[0], variable=var,
                                      command=lambda a=item[1]: self.acao_menu(a))
                else:
                    m.add_command(label=item[0], command=lambda a=item[1]: self.acao_menu(a))

        m = tk.Menu(self.root, tearoff=0)
        montar(m, self.itens_menu())
        self.menu_aberto = True  # fica paradinho enquanto o menu está aberto
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()
            self.menu_aberto = False
            self.pausa_ate = time.time() + 1.5

    def criar_icone_bandeja(self):
        def entrada(item):
            if item is None:
                return pystray.Menu.SEPARATOR
            if isinstance(item[1], list):
                return pystray.MenuItem(item[0], pystray.Menu(*[entrada(i) for i in item[1]]))
            rotulo, acao, marcado = item
            # o pystray confere quantos parâmetros cada função tem, então nada de argumento padrão aqui
            def rotulo_atual(_):  # atualiza "Mostrar/Esconder" e "Limpar fila (N)"
                return next((i[0] for i in self.itens_menu() if i and i[1] == acao), rotulo)

            def clicou(icon, _):
                self.eventos.put(("menu", acao))

            def marcado_agora(_):
                return marcado()

            return pystray.MenuItem(rotulo_atual, clicou, checked=marcado_agora if marcado else None,
                                    default=acao == "perguntar")

        menu = pystray.Menu(lambda: [entrada(i) for i in self.itens_menu()])
        DADOS.mkdir(exist_ok=True)
        imagem = desenhar_icone()
        imagem.save(DADOS / "claudinho.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
        self.icone = pystray.Icon("claudinho", imagem, "Claudinho", menu)
        self.icone.run_detached()

    def nome_frequencia(self):
        atual = list(self.cfg["comentar_a_cada_minutos"])
        for nome, a, b in FREQUENCIAS:
            if atual == [a, b]:
                return f"{nome.lower()} ({a}–{b} min)"
        return f"{atual[0]}–{atual[1]} min"

    def acao_menu(self, acao):
        if acao == "perguntar":
            if not self.visivel:
                self.acao_menu("visivel")
            if not self.entrada:
                self.alternar_entrada()
        elif acao == "visivel":
            self.visivel = not self.visivel
            if self.visivel:
                self.root.deiconify()
                self.root.attributes("-topmost", True)
            else:
                self.root.withdraw()
        elif acao.startswith("musica:"):  # ⏯ ⏭ ⏮ (em thread: o Windows responde devagar às vezes)
            comando = acao.split(":", 1)[1]
            threading.Thread(target=lambda: (musica.controlar(comando), self.atualizar_musica()),
                             daemon=True).start()
        elif acao == "esquete_agora" or acao.startswith("esquete:"):
            self.largar_esquete()
            escolhida = acao.split(":", 1)[1] if ":" in acao else ""
            # começa assim que ele estiver livre ("qualquer" = sorteia)
            self.esquete_forcada = escolhida if escolhida in esquetes.ESQUETES else "qualquer"
        elif acao.startswith("musica_buscar:"):  # painel: "toca isso aqui" no YouTube Music
            termo = acao.split(":", 1)[1].strip()[:150]
            if termo:
                self.tocar_no_youtube_music(termo)
        elif acao == "venda":
            self.aplicar_cfg("vendado", not self.cfg["vendado"])
        elif acao == "painel":
            self.abrir_painel()
        elif acao == "conversa":
            self.ver_conversa()
        elif acao in ("inicio:1", "inicio:0", "aviso:1", "aviso:0"):
            qual, ligar = acao.split(":")
            try:
                (sistema.abrir_com_windows if qual == "inicio" else sistema.ligar_aviso)(ligar == "1")
            except Exception as e:
                self.comentar(f"⚠ Não consegui: {e}", prioridade=IMPORTANTE)
        elif acao == "instalar_extensao":
            self.instalar_extensao()
        elif acao == "comentar_agora":
            self.comentar_agora()
        elif acao == "resumir":
            self.resumir_tela()
        elif acao == "notificacoes":
            self.ver_notificacoes()
        elif acao == "nova":
            self.nova_conversa()
        elif acao == "teste":
            self.eventos.put(("aviso", {
                "projeto": "teste", "pedido": "me avisa quando terminar",
                "resposta": "Isso é um aviso de teste. Quando um chat do Claude Code terminar, aparece assim."}))
        elif acao == "limpar":
            self.falas.clear()
        elif acao == "sair":
            self.fechar_painel()
            self.icone.stop()
            self.chat.fechar()
            self.root.destroy()
            return
        self.icone.update_menu()

    # ---------- painel de configurações (painel.html, servido pelo servidor local) ----------
    def aplicar_cfg(self, chave, valor):
        """Muda uma configuração vinda do painel (ou de um atalho), com os efeitos de cada uma."""
        if chave not in CHAVES_PAINEL:
            return
        if chave == "visual":
            valor = skins.visual_valido(valor)
        elif chave == "comentar_a_cada_minutos":
            valor = [int(valor[0]), int(valor[1])]
        elif chave == "chance_haiku":
            valor = max(0.0, min(1.0, float(valor)))
        elif chave == "aviso_segundos":
            valor = max(3, min(30, int(valor)))
        elif chave == "movimento":
            valor = "horizontal" if valor == "horizontal" else "livre"
        elif chave == "personalidade":
            valor = "ultron" if valor == "ultron" else "claudinho"
        elif chave == "mestre":
            valor = {"nome": str(valor.get("nome") or "").strip()[:60], "sobre": str(valor.get("sobre") or "").strip()[:4000]}
        else:
            valor = bool(valor)
        if self.cfg.get(chave) == valor:
            return
        antes = self.cfg.get(chave)
        self.mudar_cfg(chave, valor)
        if chave == "vendado":
            self.comentar("Ei, quem apagou a luz? Tô sem ver nada, pode ficar tranquilo." if valor
                          else "Voltei a enxergar! Nossa, que tela bonita.", duracao=4, prioridade=ESTADO)
        elif chave == "mestre":
            escrever_perfil(valor)
            self.chat.trocar_personalidade(self.cfg["personalidade"])  # o chat relê o perfil novo
            nome = valor["nome"]
            self.comentar(f"Prazer, {nome}! Agora eu sei quem manda aqui. 😎" if nome and nome != (antes or {}).get("nome")
                          else "Anotado! Agora eu te conheço melhor.", duracao=4, prioridade=ESTADO)
        elif chave == "personalidade":
            self.chat.trocar_personalidade(valor)
            if valor == "ultron":
                self.largar_esquete()
                self.esquete_forcada = "ultron"
            self.comentar("Finalmente. Um corpo à altura da minha mente. Este PC agora tem um novo administrador."
                          if valor == "ultron" else "Ufa, voltei a ser eu. O que foi que eu disse esse tempo todo?",
                          duracao=5, prioridade=ESTADO)
        elif chave == "modo_tdah":
            self.comentar("Modo TDAH ligado. Falando nisso, você sabia que polvo tem três corações?"
                          if valor else "Ok, foco. Voltei pro assunto.", duracao=4, prioridade=ESTADO)
        elif chave == "modo_maldoso":
            self.comentar("Modo maldoso ligado. Prepara o psicológico." if valor else "Tá bom, volto a ser fofo.",
                          duracao=4, prioridade=ESTADO)
        elif chave == "comentar_a_cada_minutos":
            self.prox_comentario = time.time() + random.uniform(*valor) * 60
        elif chave == "ver_musica" and not valor:
            self.musica = None
        elif chave == "emo_rock" and not valor:
            self.emo_ate = 0
        elif chave == "esquetes" and not valor:
            self.largar_esquete()
        elif chave == "emojis" and valor:
            self.soltar_emoji("coracao")
        elif chave == "visual":
            self.comentar(frases.roupa_nova(antes, valor, skins), duracao=4, prioridade=ESTADO)
            if self.cfg["emojis"]:
                self.soltar_emoji("coracao")  # gostou da roupa nova

    def estado_painel(self):
        """O que o painel mostra (chamado pela thread do servidor: só lê)."""
        m = self.musica
        return {
            "cfg": {k: self.cfg[k] for k in CHAVES_PAINEL},
            "frequencias": [{"nome": n, "de": a, "ate": b} for n, a, b in FREQUENCIAS],
            "atalhos": {k: self.cfg[k] for k in ("atalho_comentar", "atalho_venda", "atalho_resumir",
                                                  "atalho_notificacoes")},
            "pastas": self.cfg["pastas_leitura"],
            "skins": skins.catalogo(),
            "sprite": {"corpo": CORPO, "pernas": PERNAS, "margem": MARGEM, "folga": FOLGA,
                       "olhos_x": {str(k): v for k, v in OLHOS_X.items()},
                       "olhos_y": {str(k): v for k, v in OLHOS_Y.items()}},
            "esquetes": [{"id": k, "nome": NOMES_ESQUETES.get(k, k)} for k in esquetes.ESQUETES],
            "musica": musica.descrever(m) if m else None,
            "fila": len(self.falas),
            "lembrancas_total": self.mem.total_lembrancas(),
            "sistema": {"versao": sistema.VERSAO, "inicio": sistema.abre_com_windows(), "aviso": sistema.aviso_ligado(),
                        "claude": tem_claude(), "dados": str(DADOS), "empacotado": sistema.EMPACOTADO},
            "extensao": {"conectada": extensao_conectada(), "abas": EXT["abas"], "pasta": str(DADOS / "extensao")},
        }

    def abrir_painel(self):
        self.abrir_janela_web("/painel", "Claudinho · Painel", 1040, 760)

    def abrir_janela_web(self, caminho, titulo, w, h):
        """Abre uma página do servidor local numa janela de app do Edge (sem barra de navegador), no monitor
        do Claudinho. Se já estiver aberta, só traz pra frente."""
        url = f"http://127.0.0.1:{PORTA}{caminho}"
        aberta = next((j["hwnd"] for j in janelas.listar() if j["titulo"].startswith(titulo)), None)
        if aberta:
            user32.ShowWindow(aberta, 9)  # SW_RESTORE
            abrir.forcar_frente(aberta)
            return
        _, (esq, topo, dir_, base), _ = monitor(*self.centro())
        h = min(h, base - topo - 40)
        x, y = esq + (dir_ - esq - w) // 2, topo + max(0, (base - topo - h) // 2)
        edge = shutil.which("msedge") or next((str(c) for c in (
            Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft/Edge/Application/msedge.exe",
            Path(os.environ.get("ProgramFiles", "")) / "Microsoft/Edge/Application/msedge.exe") if c.exists()), None)
        if not edge:
            webbrowser.open(url)
            return
        user32.AllowSetForegroundWindow(-1)  # ASFW_ANY: a janela nova pode vir pra frente (você acabou de clicar)
        proc = subprocess.Popen([edge, f"--app={url}", f"--window-size={w},{h}", f"--window-position={x},{y}",
                                 # InPrivate: sem isso o Edge entra sozinho na conta Microsoft e mostra aviso de sincronizar
                                 f"--user-data-dir={DADOS / 'painel-edge'}", "--inprivate", "--disable-sync",
                                 "--no-first-run", "--no-default-browser-check", "--disable-features=Translate"],
                                creationflags=subprocess.CREATE_NO_WINDOW)
        # no mesmo "job" do chat: se o Claudinho fechar (ou for derrubado), a janela fecha junto
        ctypes.windll.kernel32.AssignProcessToJobObject(wt.HANDLE(JOB_FILHOS), wt.HANDLE(proc._handle))

        def trazer():  # o Windows deixa janela nova nascer atrás das outras: espera ela aparecer e traz
            for _ in range(40):
                time.sleep(0.25)
                nova = next((j["hwnd"] for j in janelas.listar() if j["titulo"].startswith(titulo)), None)
                if nova:
                    abrir.forcar_frente(nova)
                    return
        threading.Thread(target=trazer, daemon=True).start()

    def instalar_extensao(self):
        """Monta a extensão em ~/.claudinho/extensao (com a chave e o ícone), abre a pasta e a página de
        extensões do navegador padrão. O navegador não deixa instalar sozinho: você carrega a pasta lá."""
        destino = montar_extensao()
        os.startfile(destino)
        exe = abrir.navegador_padrao()[0] if len(abrir.navegador_padrao()) == 1 else ""
        pagina = {"opera.exe": "opera://extensions", "chrome.exe": "chrome://extensions",
                  "msedge.exe": "edge://extensions", "brave.exe": "brave://extensions"}.get(exe)
        caminho = caminho_do_navegador()
        if pagina and caminho:
            subprocess.Popen([caminho, pagina], creationflags=subprocess.CREATE_NO_WINDOW)

    @staticmethod
    def fechar_painel():
        """Fecha painel que tenha sobrado (de um Claudinho anterior, que tinha outro token)."""
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | "
                        "Where-Object { $_.CommandLine -like '*painel-edge*' } | "
                        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"],
                       creationflags=subprocess.CREATE_NO_WINDOW, timeout=20)

    def mudar_cfg(self, chave, valor):
        self.cfg[chave] = valor
        gravar_json(CONFIG, self.cfg)
        self.icone.update_menu()  # a bandeja só redesenha marquinhas e textos quando pedem
        if chave == "movimento" and valor == "horizontal":
            _, area, _ = self.area()
            self.modo, self.alvo = "passeio", (self.x, area[3] - self.H)

    # ---------- balões ----------
    def reposicionar_baloes(self):
        for b in (self.entrada, self.balao):  # a conversa primeiro: o outro balão empilha em cima dela
            if b:
                b.posicionar()

    def fechar_balao(self):
        if self.balao:
            self.balao.destruir()
            self.balao = None

    def avisos_na_fila(self):
        return sum(1 for f in self.falas if f["tipo"] == "aviso")

    def rodape_aviso(self, dados):
        partes = []
        pedido = (dados.get("pedido") or "").strip().replace("\n", " ")
        if pedido:
            partes.append("você pediu: " + (pedido[:60] + "…" if len(pedido) > 60 else pedido))
        n = self.avisos_na_fila()
        if n:
            partes.append(f"+{n} na fila")
        return "  ·  ".join(partes)

    def mostrar(self, fala):
        self.fechar_balao()
        if fala["tipo"] == "aviso":
            d = fala["dados"]
            resposta = formatar.limpar(d.get("resposta") or "(sem texto)")  # balão não entende markdown
            if len(resposta) > 1200:  # aviso é resumo: no máximo ~3 páginas
                resposta = resposta[:1200].rsplit(" ", 1)[0] + "…"
            self.balao = Balao(self, "aviso", resposta, titulo=f"✓ pronto em {d.get('projeto') or '?'}",
                               rodape=self.rodape_aviso(d), duracao=self.cfg["aviso_segundos"])
            try:
                import winsound
                winsound.MessageBeep(0x40)
            except Exception:
                pass
            self.soltar_emoji("check")  # comemora o chat que terminou
        elif fala["tipo"] == "notificacoes":  # resumo + limpar só as que ele leu (as que chegarem depois ficam)
            n = len(fala["ids"])
            self.balao = Balao(self, "notificacoes", fala["texto"], titulo=f"🔔 {n} notificaç{'ão' if n == 1 else 'ões'}",
                               duracao=fala["duracao"],
                               botoes=[("limpar", lambda: self.limpar_notificacoes(fala["ids"]), True),
                                       ("deixa", self.fechar_balao, False)])
        elif fala.get("piada") and self.cfg["modo_avaliacao"]:  # piada com botões pra avaliar
            self.balao = Balao(self, fala["tipo"], fala["texto"], duracao=fala["duracao"],
                               botoes=[("boa", lambda: self.avaliar(fala, 1), True),
                                       ("ruim", lambda: self.avaliar(fala, -1), False)],
                               botoes_no_hover=True)
        else:
            self.balao = Balao(self, fala["tipo"], fala["texto"], duracao=fala["duracao"])
        self.balao.dados = fala
        self.lembrar_fala(fala)

    # ---------- continuidade: o chat sabe o que ele falou nos balões ----------
    def lembrar_fala(self, fala):
        """Anota o que ele acabou de falar num balão (piada, comentário, aviso) pra conversa continuar dali."""
        if fala["tipo"] == "aviso":
            d = fala["dados"]
            texto = f"[aviso] pronto em {d.get('projeto') or '?'}: {formatar.limpar(d.get('resposta') or '')[:300]}"
        else:
            texto = fala.get("texto", "")
        if texto:
            self.falas_mostradas.append((time.time(), texto))

    def falas_recentes(self, minutos=15):
        agora = time.time()
        return [(agora - quando, texto) for quando, texto in self.falas_mostradas if agora - quando < minutos * 60]

    def contexto_das_falas(self):
        """Bloco que vai junto da sua mensagem: o que ele disse nos balões nos últimos minutos."""
        recentes = self.falas_recentes()
        if not recentes:
            return ""
        linhas = "\n".join(f"- há {max(1, round(seg / 60))} min: \"{texto}\"" for seg, texto in recentes)
        return ("\n\n(Contexto automático: o que você, Claudinho, falou nos balões nos últimos minutos. "
                "Se a mensagem dele for uma resposta a isso, continue a conversa a partir daí:\n" + linhas + ")")

    # ---------- confirmação antes de agir no PC ----------
    def pedir_permissao(self, ferramenta, entrada):
        """Roda na thread do chat: abre o popup e espera o Sim/Não (até 3 min; sem resposta = não)."""
        pedido = {"ferramenta": ferramenta, "entrada": entrada, "ok": False, "evento": threading.Event()}
        self.eventos.put(("permissao", pedido))
        pedido["evento"].wait(180)
        pedido["evento"].set()
        return pedido["ok"]

    def descrever_acao(self, ferramenta, entrada):
        caminho = entrada.get("file_path") or entrada.get("path") or entrada.get("pattern") or ""
        if ferramenta in ("Bash", "PowerShell"):
            texto = f"Rodar no {ferramenta}:\n{entrada.get('command', '')}"
            if entrada.get("description"):
                texto += f"\n({entrada['description']})"
        elif ferramenta == "Write":
            texto = f"Criar/sobrescrever o arquivo:\n{caminho}"
        elif ferramenta in ("Edit", "MultiEdit", "NotebookEdit"):
            texto = f"Editar o arquivo:\n{caminho}"
        elif ferramenta in ("Read", "Glob", "Grep"):
            texto = f"Ler fora das pastas liberadas:\n{caminho}"
        else:
            texto = f"Usar {ferramenta}:\n{json.dumps(entrada, ensure_ascii=False)[:300]}"
        return texto if len(texto) <= 500 else texto[:500] + "…"

    def mostrar_permissao(self, pedido):
        def responder(ok):
            pedido["ok"] = ok
            pedido["evento"].set()

        if self.balao and self.balao.tipo not in ("pensando", "comentario", "permissao"):
            self.falas.appendleft(self.balao.dados)  # volta para a fila, mostra depois
        self.fechar_balao()
        self.permissao = pedido
        self.balao = Balao(self, "permissao", self.descrever_acao(pedido["ferramenta"], pedido["entrada"]),
                           titulo="posso fazer isso?",
                           botoes=[("Pode", lambda: responder(True), True),
                                   ("Não", lambda: responder(False), False)])
        try:
            import winsound
            winsound.MessageBeep(0x30)
        except Exception:
            pass

    def conversa_deve_fechar(self):
        """Fecha a conversa se você clicou fora dela, ou se ela chegou sozinha (uma resposta) e ficou
        sem ninguém tocar até o tempo acabar. Perder o foco sem clique (uma notificação ou outro
        programa que pulou na frente) não fecha: o que você estava escrevendo continua lá."""
        if not self.entrada:
            return False
        if time.time() - self.entrada_desde < 0.6:
            user32.GetAsyncKeyState(0x01)  # descarta o clique que abriu a conversa
            return False
        try:
            nossas = {int(self.entrada.win.wm_frame(), 16), int(self.root.wm_frame(), 16)}
        except Exception:
            return False
        if self.entrada.clique_fora(desde_a_ultima=True):
            return True
        if user32.GetForegroundWindow() in nossas:
            self.entrada_teve_foco = True
            return False
        return not self.entrada_teve_foco and self.entrada.expirou()

    def cuidar_dos_baloes(self):
        if self.permissao and self.permissao["evento"].is_set():  # respondida ou esgotou o tempo
            self.permissao = None
            if self.balao and self.balao.tipo == "permissao":
                self.fechar_balao()
        if self.conversa_deve_fechar():
            self.fechar_conversa()
        if self.balao and self.balao.interagiu and self.balao.clique_fora():  # leu as páginas e clicou fora
            self.fechar_balao()
        if self.balao and self.balao.expirou():
            self.fechar_balao()
        # fala de estado velha (ficou esperando a conversa ou uma resposta) não vale mais nada
        for velha in [f for f in self.falas if f.get("prioridade", FALA) == ESTADO and time.time() - f["criada"] > 15]:
            self.falas.remove(velha)
        # chegou algo mais importante: o balão de agora sai da frente, a não ser que você esteja lendo
        # (fala de estado sai sempre; aviso/coisa que você pediu nunca é atropelado)
        if self.balao and self.falas and self.balao.tipo not in ("pensando", "permissao"):
            atual = (self.balao.dados or {}).get("prioridade", FALA)
            nova = self.falas[0].get("prioridade", FALA)
            lendo = self.balao.hover or self.balao.interagiu or self.mouse_no_mascote
            if atual == ESTADO or (nova > atual and atual < IMPORTANTE and not lendo):
                self.fechar_balao()
        livre = self.balao is None or self.balao.tipo == "pensando"
        if livre and not self.entrada and self.falas:
            # pergunta tem prioridade: enquanto pensa, os avisos esperam
            if not self.ocupado or self.falas[0]["tipo"] == "resposta":
                self.mostrar(self.falas.popleft())
        pensando = self.ocupado or self.olhando_forcado or self.lendo_notificacoes
        rotulo = ("fazendo" if self.usou_ferramenta else "digitando") if self.ocupado else \
            "lendo as notificações" if self.lendo_notificacoes else "deixa eu ver"
        if pensando and self.balao is None and not self.entrada:
            self.balao = Balao(self, "pensando", rotulo)
        if self.balao and self.balao.tipo == "pensando":
            if not pensando:
                self.fechar_balao()
            else:
                self.balao.mudar_texto(rotulo + "." * (self.t // 5 % 4) + " " * 3)
        if self.balao and self.balao.tipo == "aviso":
            self.balao.mudar_rodape(self.rodape_aviso(self.balao.dados["dados"]))
        self.reposicionar_baloes()

    # ---------- pergunta ----------
    def ultima_resposta(self):
        return self.mem.ultima_resposta()

    def fechar_conversa(self, manter_print=False):
        if self.entrada:
            self.entrada.destruir()
            self.entrada = None
        if not manter_print:  # desistiu da mensagem: o print vai junto
            self.print_anexado = None

    def alternar_print(self):
        """Link do balão de conversa: anexa (ou tira) um print da janela que você está usando."""
        if self.print_anexado:
            self.print_anexado = None
        elif self.cfg["vendado"]:  # faixa nos olhos: nada de print, nem pedido
            self.entrada.link_print.configure(text="🙈 tô vendado, sem print (Win+Shift+Y tira a faixa)")
            return
        else:
            # o balão some um instante pra não sair no print
            self.entrada.win.attributes("-alpha", 0.0)
            self.entrada.win.update()
            try:
                img, nome = self.print_da_frente()
            finally:
                self.entrada.win.attributes("-alpha", 1.0)
            mini = img.copy()
            mini.thumbnail((40, 22))  # do tamanho da linha do link: o balão quase não cresce
            self.print_anexado = {"imagem": em_jpeg(img, qualidade=85), "nome": nome, "mini": mini}
        self.entrada.mostrar_print(self.print_anexado)
        self.entrada.win.update_idletasks()
        self.entrada.posicionar()
        self.entrada.entry.focus_set()

    def alternar_entrada(self):
        if self.entrada:
            self.fechar_conversa()
        else:
            # o chat pode estar dormindo: já vai acordando enquanto você digita
            self.chat.ultimo_uso = time.time()
            threading.Thread(target=self.chat.aquecer, daemon=True).start()
            # acabou de falar algo num balão (até 3 min)? a conversa abre nisso, pra você responder a ele
            recente = self.falas_recentes(minutos=3)
            self.abrir_conversa(recente[-1][1] if recente else self.ultima_resposta(), por_clique=True)

    def abrir_conversa(self, texto, por_clique=False):
        """Um balão só: a última resposta dele em cima e o campo pra continuar a conversa embaixo."""
        texto = formatar.limpar(texto)  # o balão não entende markdown
        if texto.startswith("[aviso] "):
            texto = "✓ " + texto[len("[aviso] "):]
        rascunho = self.entrada.entry.get() if self.entrada else ""
        # estava digitando quando a resposta chegou? o balão novo já volta com o cursor no campo
        try:
            digitando = bool(self.entrada) and user32.GetForegroundWindow() == int(self.entrada.win.wm_frame(), 16)
        except Exception:
            digitando = False
        por_clique = por_clique or digitando
        self.fechar_conversa(manter_print=True)  # reabrir o balão não perde o rascunho nem o print
        if self.balao and self.balao.tipo not in ("pensando", "comentario"):
            self.falas.appendleft(self.balao.dados)  # volta para a fila, mostra depois
        self.fechar_balao()
        duracao = None if por_clique else limitar(20 + len(texto) / 12, 20, 90)
        self.entrada = Balao(self, "entrada", texto, titulo="claudinho" if texto else None,
                             duracao=duracao, entrada=True)
        self.entrada_desde, self.entrada_teve_foco = time.time(), False
        self.entrada.entry.bind("<Return>", self.enviar)
        self.entrada.entry.bind("<Escape>", lambda e: self.fechar_conversa())
        if rascunho:
            self.entrada.entry.insert(0, rascunho)
        if por_clique:  # abriu clicando nele: já pode digitar
            self.entrada.win.focus_force()
            self.root.after(60, self.entrada.entry.focus_set)

    def enviar(self, e=None):
        texto = self.entrada.entry.get().strip()
        if not texto:
            return
        if self.ocupado:
            self.entrada.entry.delete(0, "end")
            self.entrada.entry.configure(placeholder_text="calma, ainda tô pensando na outra…")
            return
        anexado = self.print_anexado
        self.fechar_conversa()
        # agora o Claudinho está em primeiro plano (você acabou de digitar nele): libera a próxima
        # janela que ele abrir (navegador, programa) pra vir pra frente em vez de abrir escondida
        user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
        pergunta = texto
        # cada mensagem relê o histórico todo: conversa de outro dia ou longa demais começa do zero,
        # levando só o finalzinho da anterior pra não perder o fio
        if self.mem.conversa_velha(MAX_PERGUNTAS_CONVERSA):
            anterior = self.mem.conversa_atual()
            self.mem.nova_conversa()
            self.chat.nova_conversa()
            fim = "\n".join(f"{'Eu' if q == 'eu' else 'Você'}: {t[:200]}" for q, t in self.mem.fim_da_conversa(anterior))
            if fim:
                pergunta += f"\n\n(Fim da nossa conversa anterior, só pra continuidade:\n{fim})"
        self.mem.registrar_mensagem("eu", f"[print: {anexado['nome']}] {texto}" if anexado else texto)
        self.pergunta_atual = texto
        self.ocupado = True
        if anexado:
            pergunta = f"(Junto vai um print da janela que estou usando: {anexado['nome']}.)\n\n" + pergunta
        pergunta += self.contexto_das_falas()  # continuidade: ele lembra da piada/aviso que acabou de mostrar
        pergunta += self.lembrancas_para(texto)
        pergunta += f"\n\n(Seu visual agora: {self.retrato()}.)"
        if self.musica:  # contexto que ele vê mas não precisa comentar
            pergunta += f"\n\n(Contexto automático, só use se fizer sentido: ele está ouvindo {musica.descrever(self.musica)}.)"
        imagem = anexado["imagem"] if anexado else None
        threading.Thread(target=lambda: self.eventos.put(("resposta", *self.chat.perguntar(pergunta, imagem))),
                         daemon=True).start()

    def lembrancas_para(self, texto):
        """Mini cérebro: lembranças de conversas e avisos antigos parecidas com a pergunta.
        A busca é local (SQLite, sem IA); só vai algo pro Claude quando acha, e no máximo ~1.000 caracteres."""
        if not self.cfg["lembrancas"]:
            return ""
        achadas = self.mem.buscar_lembrancas(texto, fora_da_conversa=self.mem.conversa_atual())
        if not achadas:
            return ""
        linhas = [f"- {l['criado_em'][:16]}: " + " ".join(l["texto"].split())[:320] for l in achadas]
        return ("\n\n(Lembranças de conversas e avisos anteriores que podem ter a ver; use só se ajudar e "
                "não diga que buscou:\n" + "\n".join(linhas) + ")")

    def nova_conversa(self):
        if not self.ocupado:
            self.mem.nova_conversa()  # a memória do dia e as piadas ficam
            self.chat.nova_conversa()
            self.comentar("Conversa nova! Pode mandar.", duracao=3, prioridade=ESTADO)

    def ver_conversa(self):
        """A conversa inteira em balões (conversa.html), numa janela que acompanha as mensagens novas."""
        self.abrir_janela_web("/conversa", "Claudinho · Conversa", 600, 780)

    # ---------- comentários sobre a tela ----------
    def acompanhar_app_ativo(self):
        """De tempos em tempos anota qual programa está em foco e desde quando."""
        if self.t % 25:
            return
        try:
            ativa = janelas.janela_ativa()
        except Exception:
            return
        exe = ativa["exe"] if ativa else ""
        if exe and exe not in janelas.IGNORAR and exe != self.app_atual:
            self.app_atual, self.app_desde = exe, time.time()

    def minutos_no_app(self):
        return (time.time() - self.app_desde) / 60

    def talvez_comentar(self):
        """A vez dele de fazer algo à toa: piada ou esquete saem do mesmo timer (mesma fila, tipos diferentes)."""
        self.acompanhar_app_ativo()
        piadas, esquetes_ligadas = self.cfg["comentar_tela"], self.cfg["esquetes"]
        if not (piadas or esquetes_ligadas) or self.comentando or time.time() < self.prox_comentario:
            return
        if self.ocupado or self.balao or self.entrada or self.falas or self.esquete or self.modo != "passeio":
            return
        a, b = self.cfg["comentar_a_cada_minutos"]
        self.prox_comentario = time.time() + random.uniform(a, b) * 60
        if esquetes_ligadas and (not piadas or random.random() < 0.35):
            self.iniciar_esquete()
        elif not tem_claude() or random.random() >= self.cfg["chance_haiku"]:
            _, _, area_total = self.area()
            self.comentar_do_banco(janelas.listar(area_total))
        else:
            self.olhar_tela()

    # ---------- memória do dia (o que foi pedido nos chats) ----------
    def avisos_de_hoje(self):
        return self.mem.avisos_de(time.strftime("%Y-%m-%d"))

    def lembrar_do_dia(self, dados):
        projeto = (dados.get("projeto") or "").strip()
        if not projeto or projeto == "teste":  # aviso de teste do menu não conta
            return
        pedido = (dados.get("pedido") or "").strip().replace("\n", " ")
        self.mem.registrar_aviso(projeto, pedido[:150])
        resultado = formatar.limpar(dados.get("resposta") or "")
        self.mem.lembrar("aviso", f"Pedido no {projeto}: {pedido[:400]}\nResultado: {resultado[:900]}", projeto)

    def resumo_do_dia(self):
        """Texto curto para o Haiku com o que foi pedido nos chats hoje."""
        dia = self.avisos_de_hoje()
        if not dia:
            return ""
        # sem o total de tarefas: o Haiku transformava "22 tarefas…" em bordão
        linhas = [f"- {a['projeto']}: \"{a['pedido'][:100]}\"" for a in dia[-5:]]
        return ("Algumas coisas que ele pediu pro Claude Code hoje (contexto opcional; só use se combinar "
                "muito com a tela, e não conte quantas tarefas foram):\n" + "\n".join(linhas))

    def print_da_frente(self):
        """Print da janela que você está usando (a mais à frente que não é do Claudinho) -> (imagem, nome).
        Quem chama confere a faixa nos olhos antes."""
        janela = janelas.janela_ativa()
        nossas = {int(w.wm_frame(), 16) for w in (self.root,) + ((self.entrada.win,) if self.entrada else ())}
        if not janela or janela["hwnd"] in nossas or janela["exe"] in janelas.IGNORAR \
                or janela["rect"][2] - janela["rect"][0] <= 200:
            # o foco está no Claudinho (você clicou nele): pega a primeira janela de verdade atrás
            janela = next(iter(janelas.listar()), None)
        if janela:
            esq, topo, dir_, base = janela["rect"]
            _, area_mon, total = monitor((esq + dir_) / 2, (topo + base) / 2)
            caixa = (max(esq, total[0]), max(topo, total[1]), min(dir_, total[2]), min(base, total[3]))
            nome = frases.NOMES.get(frases.categoria(janela), janela["exe"].replace(".exe", ""))
        else:  # sem janela útil: o monitor do mouse inteiro
            _, _, caixa = monitor(*cursor())
            nome = "tela"
        img = ImageGrab.grab(bbox=caixa, all_screens=True)
        if img.width > 1800:  # texto precisa de resolução: reduz só se for muito grande
            img = img.resize((1800, round(img.height * 1800 / img.width)))
        return img, nome

    # ---------- notificações do Windows ----------
    def ver_notificacoes(self):
        """Menu ou atalho: lê a central de notificações, o Haiku resume e o balão oferece limpar."""
        if self.lendo_notificacoes:
            return
        if not tem_claude():
            self.comentar(SEM_CLAUDE, prioridade=IMPORTANTE)
            return
        self.lendo_notificacoes = True

        def trabalho():
            try:
                lista = notificacoes.listar()
                resumo = resumir_notificacoes(lista) if lista else ""
                self.eventos.put(("notificacoes", resumo, [n["id"] for n in lista], None))
            except Exception as e:
                self.eventos.put(("notificacoes", "", [], str(e)))
        threading.Thread(target=trabalho, daemon=True).start()

    def limpar_notificacoes(self, ids):
        self.fechar_balao()
        threading.Thread(target=lambda: notificacoes.limpar(ids), daemon=True).start()
        self.comentar(f"Prontinho, limpei {len(ids)} notificaç{'ão' if len(ids) == 1 else 'ões'}! ✨", duracao=4,
                      prioridade=ESTADO)

    def resumir_tela(self):
        """Atalho: print da janela da frente vai pro chat dele, pedindo um resumo bem simples.
        A resposta cai no balão de conversa, então dá pra continuar perguntando sobre o mesmo print."""
        if not tem_claude():
            self.comentar(SEM_CLAUDE, prioridade=IMPORTANTE)
            return
        if self.cfg["vendado"]:
            self.comentar("Tô vendado, não dá pra ler nada! Tira a faixa (Win+Shift+Y) que eu leio.", duracao=5,
                          prioridade=ESTADO)
            return
        if self.ocupado:
            self.comentar("Calma, ainda tô pensando na outra…", duracao=3, prioridade=ESTADO)
            return
        img, nome = self.print_da_frente()
        pedido = ("Este é um print da janela que estou vendo agora (" + nome + "). Me explica o que tem nela "
                  "de forma BEM simplificada: se for um texto longo, resume em poucos tópicos curtos e fáceis; "
                  "se for código ou erro, diz o que é e o que fazer; se for outra coisa, explica em 2-3 frases. "
                  "Não descreva a interface, foque no conteúdo.")
        self.mem.registrar_mensagem("eu", f"[print da janela: {nome}] me resume isso")
        self.pergunta_atual = f"[print da janela: {nome}] me resume isso"
        self.ocupado = True
        self.usou_ferramenta = True  # balão mostra "fazendo…" e ele saca o notebook
        imagem = em_jpeg(img, qualidade=88)  # mais nítido: é pra ler texto

        # Sonnet (com o mesmo pensamento leve) só aqui: resumo precisa ler direito; o resto segue no Haiku
        threading.Thread(target=lambda: self.eventos.put(("resposta", *self.chat.perguntar(pedido, imagem, "sonnet"))),
                         daemon=True).start()

    def comentar_agora(self):
        """Menu ou atalho: sempre olha a tela de verdade (Haiku), mostrando que está olhando."""
        if self.comentando:
            return
        if self.cfg["vendado"]:
            self.comentar("Tô vendado, não dá pra ver nada! Tira a faixa no menu se quiser que eu olhe.", duracao=5,
                          prioridade=ESTADO)
            return
        self.olhando_forcado = True
        if self.balao and self.balao.tipo == "comentario":
            self.fechar_balao()
        self.olhar_tela()

    def emo_agora(self):
        m = self.musica
        return bool(time.time() < self.emo_ate and m and m["tocando"] and (m["titulo"], m["artista"]) == self.emo_musica)

    def retrato(self):
        """Como ele está agora (cor, adereços, emo, venda), numa frase: é assim que ele "se enxerga"."""
        return skins.autorretrato(self.cfg["visual"], self.emo_agora(), self.cfg["vendado"])

    def sortear_alvo(self, area_total):
        """Do que a piada vai falar: o que ele faz, o que está perto do mouse ou perto do Claudinho.
        Devolve (alvo, ponto na tela ou None)."""
        alvo = random.choices(list(PESOS_ALVO), weights=list(PESOS_ALVO.values()))[0]
        mx, my = cursor()
        esq, topo, dir_, base = area_total
        if alvo == "mouse" and esq <= mx < dir_ and topo <= my < base:
            return "mouse", (mx, my)
        if alvo == "claudinho":
            return "claudinho", tuple(int(v) for v in self.centro())
        if alvo == "eu_mesmo":
            return "eu_mesmo", None
        return "atividade", None

    def olhar_tela(self):
        _, _, area_total = self.area()
        lista = janelas.listar(area_total)
        if self.cfg["vendado"]:  # de faixa nos olhos: nada de print, só o banco de frases
            self.olhando_forcado = False
            self.comentar_do_banco(lista)
            return
        self.comentando = True
        modelo, recentes, assuntos = (self.cfg["modelo_comentario"], self.mem.piadas_recentes(25),
                                      self.mem.assuntos_recentes(8))
        maldoso, tdah = self.cfg["modo_maldoso"], self.cfg["modo_tdah"]
        alvo, ponto = self.sortear_alvo(area_total)
        eu, retrato = tuple(int(v) for v in self.centro()), self.retrato()
        contexto = (f"Programa em foco: {self.app_atual}, há {int(self.minutos_no_app())} minutos.\n"
                    if self.app_atual else "") + self.resumo_do_gosto() + perfil_curto(self.cfg["mestre"])
        if maldoso or tdah:  # nesses modos a piada é sobre a tela: segundo plano fica de fora
            contexto += SO_O_QUE_ESTA_NA_TELA
        else:
            contexto += self.resumo_do_dia()
            if self.musica and self.musica["tocando"]:
                contexto += f"\nEle está ouvindo agora: {musica.descrever(self.musica)}."

        def trabalho():
            try:
                r = comentar_tela(area_total, modelo, recentes, lista, contexto, maldoso, tdah, alvo, ponto,
                                  assuntos, eu=eu, retrato=retrato, personalidade=self.cfg["personalidade"])
            except Exception:
                r = None
            self.eventos.put(("comentario", r, lista, alvo))

        threading.Thread(target=trabalho, daemon=True).start()

    def comentar_do_banco(self, lista):
        """Comentário sem IA: escolhe a janela do alvo sorteado e uma frase do banco."""
        _, _, area_total = self.area()
        alvo, ponto = self.sortear_alvo(area_total)
        janela = janelas.no_ponto(lista, *ponto) if ponto else None
        if janela is None and lista:
            janela = next((j for j in lista if j["exe"] == self.app_atual), lista[0])
        minutos = self.minutos_no_app() if janela and janela["exe"] == self.app_atual else 0
        if self.cfg["personalidade"] == "ultron" and random.random() < 0.7:
            modelo, texto = frases.ultron(janela, minutos, self.mem.modelos_recentes(40))
        elif random.random() < 0.12:  # autoconfiança: de vez em quando ele se elogia
            modelo, texto = frases.autoelogio(skins.itens_vestidos(self.cfg["visual"]),
                                              skins.CORES[self.cfg["visual"]["cor"]]["nome"].lower(),
                                              self.emo_agora(), self.mem.modelos_recentes(40))
        else:
            modelo, texto = frases.escolher(janela, minutos, self.mem.modelos_recentes(40), self.cfg["modo_maldoso"],
                                            self.avisos_de_hoje(), self.cfg["modo_tdah"], self.notas_do_banco(),
                                            self.musica)
        pid = self.lembrar_piada(texto, "banco", modelo=modelo, alvo=alvo)
        self.comentar(texto, {"origem": "banco", "id": pid})

    def categoria_atual(self):
        try:
            ativa = janelas.janela_ativa()
        except Exception:
            ativa = None
        return frases.categoria(ativa) if ativa else "geral"

    def lembrar_piada(self, texto, origem, assunto="", modelo=None, alvo=None):
        """Guarda a piada no banco com o contexto em que saiu (pra notas e pra buscar exemplos parecidos)."""
        tocando = self.musica["titulo"] if self.musica and self.musica["tocando"] else None
        return self.mem.registrar_piada(texto, origem, modelo, assunto, {
            "categoria": self.categoria_atual(), "app": self.app_atual, "alvo": alvo,
            "maldoso": self.cfg["modo_maldoso"], "tdah": self.cfg["modo_tdah"], "musica": tocando})

    def parecida(self, texto, assunto=""):
        """Piada nova repete alguma já dita ou já avaliada? Pega mesmo assunto, mesmo começo, texto
        ~parecido ou um trecho marcante em comum ("pão de queijo", "# tarefas e você"). Números
        contam como iguais: "22 tarefas" e "25 tarefas" são a mesma piada."""
        if assunto and any(SequenceMatcher(None, assunto, a).ratio() > 0.7 for a in self.mem.assuntos_recentes(8)):
            return True
        novo = normalizar(texto)
        inicio, trechos = novo[:4], trechos_marcantes(novo)
        ja_ditas = self.mem.piadas_recentes(25) + self.mem.textos_avaliados(60)
        for antiga in ja_ditas:
            antiga = normalizar(antiga)
            if (antiga[:4] == inicio or trechos & trechos_marcantes(antiga)
                    or SequenceMatcher(None, " ".join(novo), " ".join(antiga)).ratio() > 0.55):
                return True
        return False

    def comentar(self, texto, piada=None, duracao=8, prioridade=FALA):
        """Comenta de onde está. `piada` (origem etc.) marca que é piada: aí dá pra avaliar.
        `prioridade`: ESTADO (vendei, modo ligado…: some se vier outra coisa), FALA (piada, comentário)
        ou IMPORTANTE (aviso, coisa que você pediu, erro: nunca é atropelada)."""
        self.enfileirar({"tipo": "comentario", "texto": texto, "duracao": duracao, "piada": piada},
                        prioridade)

    def enfileirar(self, fala, prioridade=FALA, na_frente=False):
        """Põe a fala na fila na ordem de prioridade (as mais importantes passam na frente das menores).
        Fala de estado substitui outra de estado que ainda nem apareceu: só vale a última."""
        fala.update(prioridade=prioridade, criada=time.time())
        if prioridade == ESTADO:
            for velha in [f for f in self.falas if f.get("prioridade", FALA) == ESTADO]:
                self.falas.remove(velha)
        pos = next((i for i, f in enumerate(self.falas)
                    if f.get("prioridade", FALA) < prioridade or (na_frente and f.get("prioridade", FALA) == prioridade)),
                   len(self.falas))
        self.falas.insert(pos, fala)

    # ---------- reações (emojis que sobem flutuando) ----------
    # ---------- esquetes (idle: deploy do nada, café, cochilo…) ----------
    def cuidar_da_esquete(self):
        agora = time.time()
        if self.esquete:
            # você chamou (clicou, arrastou, pediu algo) ou ele saiu correndo: larga tudo, sem fala de fim
            chegou_importante = any(f.get("prioridade", FALA) == IMPORTANTE for f in self.falas)
            if (self.ocupado or self.arrasto or self.entrada or chegou_importante or self.lendo_notificacoes
                    or self.modo != "passeio" or not self.visivel):
                self.largar_esquete()
            elif self.esquete["nome"] == "inseto":
                self.cuidar_do_inseto(agora)
            elif self.esquete["nome"] == "construindo":
                self.cuidar_da_construcao(agora)
            elif agora >= self.esquete["ate"]:
                fim, emoji = esquetes.final(self.esquete["nome"], self.cfg["personalidade"] == "ultron")
                self.esquete = None
                if fim:
                    self.comentar(fim, duracao=5)
                if emoji and self.cfg["emojis"]:
                    self.soltar_emoji(emoji)
            return
        # "Esquete agora" (painel): roda assim que ele estiver livre
        if self.esquete_forcada and not (
                self.balao or self.entrada or self.falas or self.ocupado or self.arrasto or self.emoji
                or self.comentando or self.lendo_notificacoes or self.modo != "passeio" or not self.visivel):
            self.iniciar_esquete()

    def iniciar_esquete(self):
        agora = time.time()
        tocando = bool(self.musica and self.musica["tocando"])
        escolhida, self.esquete_forcada = self.esquete_forcada, None
        nome = self.ultima_esquete = (escolhida if escolhida in esquetes.ESQUETES
                                      else esquetes.sortear(self.ultima_esquete, tocando,
                                                            self.cfg["personalidade"] == "ultron"))
        self.esquete = {"nome": nome, "inicio": agora, "ate": agora + esquetes.ESQUETES[nome]["duracao"],
                        "musica": tocando}
        self.alvo = None  # para onde está
        inicio = esquetes.fala(nome, "inicio", tocando, self.cfg["personalidade"] == "ultron")
        if inicio:
            self.comentar(inicio, duracao=4)
        emoji = esquetes.ESQUETES[nome].get("emoji_inicio")
        if emoji and self.cfg["emojis"]:
            self.soltar_emoji(emoji)
        if nome == "inseto":
            self.criar_inseto()
        elif nome == "construindo":
            self.criar_robo()

    def desenhar_projeto_secreto(self, fase, quadrado):
        """O que fica em volta dele: o "!" do flagra e a notinha do assobio disfarçando."""
        dt = self.depois_do_flagra()
        if dt is None:
            return
        if dt < FLAGRA_SUSTO:
            quadrado(11.2, -1.6, "#f4efe4", 0.5)
            quadrado(11.2, -1.1, "#f4efe4", 0.5)
            quadrado(11.2, -0.1, "#f4efe4", 0.5)
        if dt >= FLAGRA_PUF:
            sobe = (self.t // 3) % 4 * 0.4
            quadrado(11.5, 0.6 - sobe, NB_TECLA, 0.6)
            quadrado(12.0, -0.4 - sobe, NB_TECLA, 0.25)
            quadrado(12.0, -0.15 - sobe, NB_TECLA, 0.25)

    # ----- esquete do projeto secreto: monta um Claudinho robô do tamanho dele, de lá pra cá -----
    def criar_robo(self):
        _, area, _ = self.area()
        # o robô fica do lado que tem espaço (e com espaço pra ele trabalhar dos dois lados)
        lado = -1 if self.x - area[0] > area[2] - (self.x + self.W) else 1
        x = limitar(self.x + lado * self.W * 1.0, area[0] + self.W, area[2] - 2 * self.W)
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-transparentcolor", CHAVE)
        win.config(bg=CHAVE)
        canvas = tk.Canvas(win, width=self.W, height=self.H, bg=CHAVE, highlightthickness=0)
        canvas.pack()
        fora_da_barra(win)
        tk.Wm.wm_geometry(win, f"{self.W}x{self.H}+{int(x)}+{int(self.y)}")
        self.esquete.update(robo={"win": win, "canvas": canvas, "x": x, "y": self.y},
                            montando=True, ponto=0, ate_ponto=0, acao=None)
        self.desenhar_robo(0.0)

    def desenhar_robo(self, fase):
        """O Claudinho robô: mesmo corpo dele em metal, montado de baixo pra cima; olhos acendem no fim;
        faíscas no lado em que ele está trabalhando; poeira quando some."""
        r, S = self.esquete["robo"], self.S
        c = r["canvas"]
        c.delete("all")
        oy = FOLGA * S

        def px(col, lin, cor, lado=1.0):
            x0, y0 = (col + MARGEM) * S, oy + lin * S
            c.create_rectangle(x0, y0, x0 + lado * S, y0 + lado * S, fill=cor, width=0)

        dt = self.depois_do_flagra()
        if dt is not None and dt >= FLAGRA_SUSTO:  # puf! só a poeira, abrindo e sumindo
            abre = min(1.0, (dt - FLAGRA_SUSTO) / (FLAGRA_PUF - FLAGRA_SUSTO))
            if abre < 1:
                for col, lin in ((3, 3), (6, 2), (8, 4), (2, 5), (5, 5), (7, 1), (4, 1)):
                    px(col - abre * 1.5 * (col < 5) + abre * 1.5 * (col >= 5), lin - abre * 1.2, POEIRA, 1 + abre)
            return
        pecas = [(col, lin) for lin in (7, 6) for col in PERNAS] + \
                [(col, lin) for lin in range(len(CORPO) - 1, -1, -1) for col, ch in enumerate(CORPO[lin]) if ch == "X"] + \
                [(5, -1)]  # antena
        prontas = len(pecas) if fase >= 0.58 or dt is not None else int(len(pecas) * max(0.0, fase - 0.04) / 0.54)
        for col, lin in pecas[:prontas]:
            px(col, lin, ROBO_ESCURO if lin == -1 or (lin in (3, 4) and col in (0, 10)) else ROBO)
        if prontas == len(pecas):
            vermelho = "#ff3b30" if self.t % 8 < 6 else "#7a1a14"
            px(5, -1.8, vermelho, 0.8)  # bolinha da antena
            l1, l2 = OLHOS_Y[0]
            for col in OLHOS_X[0]:
                px(col, l1, vermelho)
                px(col, l2, vermelho)
        acao = self.esquete.get("acao")
        if acao and not self.movendo and dt is None and self.t % 2 == 0:  # faíscas do lado onde ele trabalha
            borda = -0.8 if self.x < r["x"] else 10.9
            cores = {"martelo": (FOGO_3, "#fff3b0"), "solda": ("#bfe6ff", "#ffffff"), "parafuso": (POEIRA, "#d0cbc0")}[acao]
            for k in range(3):
                px(borda + ((self.t + k) % 3 - 1) * 0.4, 2 + ((self.t * 3 + k * 5) % 9) * 0.4, cores[k % 2], 0.35)

    def depois_do_flagra(self):
        """Segundos desde que ele percebeu que você estava olhando (None = ainda montando)."""
        flagra = self.esquete and self.esquete.get("flagra")
        return time.time() - flagra if flagra else None

    def cuidar_da_construcao(self, agora):
        e = self.esquete
        fase = (agora - e["inicio"]) / esquetes.ESQUETES["construindo"]["duracao"]
        dt = self.depois_do_flagra()
        if dt is not None and dt >= FLAGRA_FIM:  # terminou: robô já sumiu, fala de disfarce
            self.largar_esquete()
            fim, emoji = esquetes.final("construindo", self.cfg["personalidade"] == "ultron")
            if fim:
                self.comentar(fim, duracao=5)
            return
        if e["montando"] and fase >= 0.6 and not self.movendo:  # robô pronto (e ele num dos lados)… e aí percebe você
            e.update(montando=False, acao=None, flagra=agora)
            self.alvo, self.pausa_ate = None, agora + 10
        if e["montando"] and agora >= e["ate_ponto"] and not self.movendo:
            # próximo lugar de trabalho: um lado do robô ou o outro, e uma ação diferente
            _, area, _ = self.area()
            r = e["robo"]
            e["ponto"] = 1 - e["ponto"]
            alvo_x = r["x"] + (-1 if e["ponto"] == 0 else 1) * self.W * 0.82  # colado no robô (com espaço pro braço)
            self.alvo = self.limitar_na_area(alvo_x, r["y"], area)
            e["acao"] = random.choice([a for a in ("martelo", "solda", "parafuso") if a != e["acao"]])
            e["ate_ponto"] = agora + random.uniform(2.0, 3.2)
        if e["montando"] and self.movendo:
            e["robo"]["win"].lift()  # trocando de lado: ele passa por trás do robô, não por cima
        if dt is not None and dt >= FLAGRA_PUF and not e.get("sumiu"):
            e["sumiu"] = True
            e["robo"]["win"].withdraw()
        if not e.get("sumiu"):
            self.desenhar_robo(fase)

    def cacando(self):
        """Indo atrás do bug da esquete do inseto (vai correndo)."""
        return bool(self.esquete and self.esquete.get("fase_inseto") == "cacando")

    def anda_na_esquete(self):
        """Esquetes em que ele se move (sempre correndo, com pressa): caçando o bug, ou indo de um lado pro outro
        do robô que está montando escondido."""
        return self.cacando() or bool(self.esquete and self.esquete.get("montando"))

    def largar_esquete(self):
        if self.esquete and self.esquete.get("inseto"):
            self.esquete["inseto"]["win"].destroy()
        if self.esquete and self.esquete.get("robo"):
            self.esquete["robo"]["win"].destroy()
        self.esquete = None

    # ----- esquete do inseto: aparece um bichinho perto, ele vai lá e come -----
    def criar_inseto(self):
        P = max(3, self.S * 2 // 3)
        w, h = 7 * P, 5 * P
        _, area, _ = self.area()
        meio = self.x + self.W / 2
        lado = random.choice((-1, 1))
        if not area[0] + 20 < meio + lado * 250 < area[2] - 20:  # sem espaço desse lado: nasce do outro
            lado = -lado
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-transparentcolor", CHAVE)
        win.config(bg=CHAVE)
        canvas = tk.Canvas(win, width=w, height=h, bg=CHAVE, highlightthickness=0)
        canvas.pack()
        fora_da_barra(win)
        self.esquete.update(fase_inseto="notou", desde=time.time(), inseto={
            "win": win, "canvas": canvas, "P": P, "w": w, "h": h,
            "x": meio + lado * random.uniform(180, 300) - w / 2, "y": self.y + self.H - h,  # no "chão" dele
            "vx": random.choice((-1, 1)) * random.uniform(0.5, 1.0) * P / 3})
        self.desenhar_inseto()

    def desenhar_inseto(self):
        i = self.esquete["inseto"]
        P, c = i["P"], i["canvas"]
        c.delete("all")
        quadro = esquetes.INSETO[(self.t // 3) % 2]
        for lin, linha in enumerate(quadro):
            for col, ch in enumerate(linha):
                if ch != ".":
                    x = col if i["vx"] >= 0 else 6 - col  # cabeça pro lado que anda
                    c.create_rectangle(x * P, lin * P, (x + 1) * P, (lin + 1) * P,
                                       fill=esquetes.CORES_INSETO[ch], width=0)
        tk.Wm.wm_geometry(i["win"], f"{i['w']}x{i['h']}+{int(i['x'])}+{int(i['y'])}")

    def cuidar_do_inseto(self, agora):
        e, i = self.esquete, self.esquete["inseto"]
        if e["fase_inseto"] == "comendo":
            if agora - e["desde"] > 1.3:  # nhac nhac… pronto
                self.esquete = None
                self.comentar(esquetes.fala("inseto", "fim", ultron=self.cfg["personalidade"] == "ultron"), duracao=5)
                self.soltar_emoji("check")
            return
        # o bichinho anda de um lado pro outro, às vezes muda de ideia, sem sair do monitor
        _, area, _ = self.area()
        if random.random() < 0.02:
            i["vx"] = -i["vx"]
        i["x"] += i["vx"]
        if not area[0] < i["x"] < area[2] - i["w"]:
            i["vx"] = -i["vx"]
            i["x"] = limitar(i["x"], area[0], area[2] - i["w"])
        self.desenhar_inseto()
        if e["fase_inseto"] == "notou":  # vê o bicho, fala e só depois vai atrás
            if agora - e["desde"] > 1.5:
                e["fase_inseto"] = "cacando"
            return
        if agora >= e["ate"]:  # não alcançou: o bug fugiu
            self.largar_esquete()
            self.comentar(esquetes.fala("inseto", "fugiu", ultron=self.cfg["personalidade"] == "ultron"), duracao=5)
            return
        meio_bicho = i["x"] + i["w"] / 2
        if abs(self.x + self.W / 2 - meio_bicho) < self.W * 0.25:  # pegou!
            i["win"].destroy()
            e.update(fase_inseto="comendo", desde=agora, inseto=None)
            self.alvo, self.pausa_ate = None, agora + 3
            return
        # vai atrás dele (o mover cuida do passo; o alvo é atualizado todo tick)
        self.alvo = self.limitar_na_area(meio_bicho - self.W / 2, i["y"] + i["h"] - self.H, area)

    def talvez_emoji(self):
        if not self.cfg["emojis"] or self.emoji or time.time() < self.prox_emoji:
            return
        if self.balao or self.entrada or self.ocupado or self.arrasto or self.esquete or not self.visivel:
            return
        self.prox_emoji = time.time() + random.uniform(60, 180)
        ativa = next((j for j in janelas.listar() if j["exe"] == self.app_atual), None)
        categoria = frases.categoria(ativa) if ativa else "geral"
        tocando = bool(self.musica and self.musica["tocando"])
        nome = emojis.escolher(categoria, self.minutos_no_app() if ativa else 0, tocando)
        self.soltar_emoji(nome, com_frase=random.random() < 0.4)

    def soltar_emoji(self, nome, com_frase=False):
        if self.emoji or not self.cfg["emojis"]:
            return
        P = max(3, self.S * 2 // 3)  # tamanho do "pixel" do emoji
        lado = 9 * P
        win = tk.Toplevel(self.root)  # só um Canvas dentro: nada de widget do CTk aqui
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-transparentcolor", CHAVE)
        win.config(bg=CHAVE)
        canvas = tk.Canvas(win, width=lado, height=lado, bg=CHAVE, highlightthickness=0)
        canvas.pack()
        fora_da_barra(win)
        self.emoji = {"win": win, "canvas": canvas, "dados": emojis.EMOJIS[nome], "inicio": time.time(),
                      "P": P, "lado": lado, "direcao": random.choice((-1, 1))}
        if com_frase and not self.balao and not self.falas:
            self.comentar(random.choice(emojis.EMOJIS[nome]["frases"]), duracao=4)
        self.animar_emoji()

    def animar_emoji(self):
        """Sobe ~40px balançando de leve, trocando os quadros, e some no fim."""
        e = self.emoji
        if not e:
            return
        passou = time.time() - e["inicio"]
        if passou > 2.6:
            e["win"].destroy()
            self.emoji = None
            return
        P, lado, dados = e["P"], e["lado"], e["dados"]
        quadro = dados["quadros"][int(passou / 0.3) % len(dados["quadros"])]
        c = e["canvas"]
        c.delete("all")
        for lin, linha in enumerate(quadro):
            for col, ch in enumerate(linha):
                if ch != ".":
                    c.create_rectangle(col * P, lin * P, (col + 1) * P, (lin + 1) * P,
                                       fill=dados["cores"][ch], width=0)
        cx = self.x + self.W / 2 + e["direcao"] * self.W * 0.45
        x = int(cx - lado / 2 + math.sin(passou * 6) * 3)
        y = int(self.y + FOLGA * self.S - lado - passou * 16)
        tk.Wm.wm_geometry(e["win"], f"{lado}x{lado}+{x}+{y}")
        e["win"].attributes("-alpha", 1.0 if passou < 2.0 else max(0.0, (2.6 - passou) / 0.6))

    # ---------- avaliação das piadas ----------
    def avaliar(self, fala, nota):
        piada = fala.get("piada") or {}
        pid = piada.get("id") or self.lembrar_piada(fala["texto"], piada.get("origem"))
        self.mem.avaliar(pid, nota)
        self.fechar_balao()

    def notas_do_banco(self):
        """Soma das notas por frase do banco: negativas somem, positivas aparecem mais."""
        return self.mem.notas_por_modelo()

    def resumo_do_gosto(self):
        """Exemplos pro Haiku do que você curtiu e do que não curtiu.
        Antes era "faça mais nesse estilo" e ele COPIAVA a piada aprovada (o "pão de queijo" virou
        bordão); agora as curtidas servem só pra calibrar o tipo de humor, e repetir é proibido.
        Os exemplos vêm do banco priorizando a mesma situação (programa e modo) — o RAG leve."""
        situacao = (self.categoria_atual(), self.cfg["modo_maldoso"], self.cfg["modo_tdah"])
        boas = self.mem.exemplos(1, *situacao, n=6)
        ruins = self.mem.exemplos(-1, *situacao, n=6)
        partes = []
        if boas:
            partes.append(
                "Piadas que ele CURTIU, só pra você entender o tipo de humor dele (tom, tamanho, ousadia). "
                "NÃO reaproveite nenhuma imagem, comparação, bordão ou palavra marcante delas; a nova "
                "tem que ser original: " + " | ".join(boas))
        if ruins:
            partes.append("Piadas que ele NÃO curtiu (evite esse tipo de humor): " + " | ".join(ruins))
        return "\n" + "\n".join(partes) if partes else ""

    # ---------- eventos vindos de threads ----------
    def processar_eventos(self):
        while True:
            try:
                ev = self.eventos.get_nowait()
            except queue.Empty:
                return
            if ev[0] == "permissao":
                self.mostrar_permissao(ev[1])
            elif ev[0] == "ferramenta":  # ele está mexendo no PC (abrindo algo, rodando comando)
                self.usou_ferramenta = True
            elif ev[0] == "musica_nova":
                if ev[1].get("rock") and self.cfg["emo_rock"]:  # rock: vira emo um tempinho e solta um desabafo
                    self.emo_ate = time.time() + 45
                    self.emo_musica = (ev[1]["titulo"], ev[1]["artista"])
                    if not (self.balao or self.entrada):
                        self.comentar(random.choice(EMO), duracao=6)
                else:
                    self.talvez_comentar_musica(ev[1])
            elif ev[0] == "comentario_musica":
                self.comentando = False
                if ev[1] and not self.parecida(ev[1]):
                    pid = self.lembrar_piada(ev[1], "musica")
                    self.comentar(ev[1], {"origem": "musica", "id": pid})
                    self.soltar_emoji("nota")
            elif ev[0] == "menu":
                self.acao_menu(ev[1])
            elif ev[0] == "painel_cfg":
                self.aplicar_cfg(ev[1], ev[2])
            elif ev[0] == "musica_pedida":
                _, termo, m = ev
                if m:
                    self.comentar(f"🎵 Bora: {m['titulo']} - {m['artista']}. Depois segue num rádio parecido.",
                                  duracao=5, prioridade=ESTADO)
                    self.soltar_emoji("nota")
                else:
                    self.comentar(f"Não achei \"{termo}\" no YouTube Music. 🤔", duracao=5, prioridade=ESTADO)
            elif ev[0] == "notificacoes":
                self.lendo_notificacoes = False
                _, resumo, ids, erro = ev
                if erro:
                    self.comentar(f"⚠ Não consegui ler as notificações: {erro[:200]}", prioridade=IMPORTANTE)
                elif not ids:
                    self.comentar("Central de notificações limpinha, nada pra ver! ✨", duracao=5,
                                  prioridade=IMPORTANTE)
                else:  # na frente da fila: foi você que pediu
                    self.enfileirar({"tipo": "notificacoes", "texto": resumo, "duracao": 90, "ids": ids},
                                    IMPORTANTE, na_frente=True)
            elif ev[0] == "atalho_ocupado":
                self.comentar(prioridade=IMPORTANTE, texto=f"O atalho {ev[1]} já é usado por outro programa. "
                              "Troca o \"atalho_comentar\" no config.json.")
            elif ev[0] == "aviso":
                self.enfileirar({"tipo": "aviso", "dados": ev[1]}, IMPORTANTE)
                self.lembrar_do_dia(ev[1])
            elif ev[0] == "resposta":
                self.usou_ferramenta = False
                _, resposta, sid, erro = ev
                self.ocupado = False
                self.mem.guardar_meta("session_id", sid)
                # o balão não mostra markdown: tira os ** e ` que às vezes vêm na resposta
                texto = f"⚠ {erro}" if erro else formatar.limpar(resposta)
                if not erro:
                    self.mem.registrar_mensagem("claudinho", resposta)
                    self.mem.lembrar("chat", f"Você: {self.pergunta_atual[:500]}\nClaudinho: {resposta[:900]}",
                                     conversa=self.mem.conversa_atual())
                self.fechar_balao()  # tira o "pensando…"
                self.abrir_conversa(texto)  # resposta já vem com o campo pra continuar
            elif ev[0] == "comentario":
                self.comentando = False
                forcado, self.olhando_forcado = self.olhando_forcado, False
                _, r, lista, alvo = ev
                if self.modo != "passeio" and not forcado:
                    continue
                # Haiku falhou, ou repetiu uma piada recente com outras palavras: vai de banco de frases
                if not r or self.parecida(*r):
                    self.comentar_do_banco(lista)
                    continue
                texto, assunto = r
                pid = self.lembrar_piada(texto, "haiku", assunto=assunto, alvo=alvo)
                self.comentar(texto, {"origem": "haiku", "id": pid})

    def boas_vindas(self):
        self.comentar("Oi! Eu sou o Claudinho. 👋 Abri o painel pra você me conhecer: lá dá pra dizer quem você é, "
                      "me vestir e escolher se eu abro junto com o Windows.", duracao=15, prioridade=IMPORTANTE)
        self.abrir_janela_web("/painel?bemvindo=1", "Claudinho · Painel", 1040, 760)

    def rodar(self):
        if (DADOS / "extensao" / "manifest.json").exists():
            try:
                montar_extensao()
            except Exception as e:
                print("não consegui atualizar a extensão:", e, file=sys.stderr)
        # painel que ficou aberto de um Claudinho anterior não fala mais com este: fecha
        threading.Thread(target=self.fechar_painel, daemon=True).start()
        self.root.mainloop()


def main():
    if sys.stderr is None:  # aberto pelo pythonw: sem console, os erros iriam pro nada; vão pro erros.log
        DADOS.mkdir(exist_ok=True)
        sys.stderr = open(DADOS / "erros.log", "a", encoding="utf-8", buffering=1)
        print(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} Claudinho abriu", file=sys.stderr)
    eventos = queue.Queue()
    # num reinício o Claudinho antigo pode levar uns segundos pra soltar a porta: espera antes de desistir
    for tentativa in range(16):
        try:
            iniciar_servidor(eventos)
            break
        except OSError:
            if tentativa == 15:
                print("porta ocupada: já tem um Claudinho rodando", file=sys.stderr)
                r = tk.Tk()
                r.withdraw()
                r.attributes("-topmost", True)  # o aviso não pode ficar escondido atrás das janelas
                messagebox.showinfo("Claudinho", "O Claudinho já está rodando.", parent=r)
                return
            time.sleep(0.5)
    Claudinho(eventos).rodar()


if __name__ == "__main__":
    main()
