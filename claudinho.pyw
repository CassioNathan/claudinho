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
import shutil
import subprocess
import threading
import unicodedata
import time
import tkinter as tk
from collections import deque
from difflib import SequenceMatcher
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw, ImageGrab

import frases
import janelas
import emojis
import memoria
import musica

PORTA = 47821
DADOS = Path.home() / ".claudinho"
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
    "modelo_comentario": "haiku",        # modelo barato/rápido para olhar a tela
    "aviso_segundos": 5,
    "atalho_comentar": "Win+Y",          # atalho global: comenta a tela na hora
    "atalho_venda": "Win+Shift+Y",       # atalho global: põe/tira a faixa nos olhos
    "atalho_resumir": "Win+Shift+E",     # atalho global: resume/explica a janela da frente
    # onde o chat lê arquivos sem perguntar; fora daqui (e qualquer comando ou edição) pede confirmação
    "pastas_leitura": ["D:\\Projetos", "E:\\Stompdesk Projeto"],
}

FREQUENCIAS = [("Bastante", 1, 3), ("Normal", 4, 10), ("De vez em quando", 15, 30)]

CHAVE = "#010203"  # cor que vira transparente nas janelas
LARANJA = "#d97757"
OLHO = "#1f1e1d"
POEIRA = "#b9b4a8"
NB_BASE = "#3b3a37"   # notebook: base/teclado
NB_TAMPA = "#a8a59d"  # notebook: tampa (vista de trás)
NB_TECLA = "#f4efe4"
VENDA = "#2f3f63"         # faixa nos olhos (pano azul-marinho)
VENDA_BRILHO = "#4a5d8a"
FUNDO = "#262624"
FUNDO2 = "#3a3936"
TEXTO = "#ece9e1"
APAGADO = "#9b978d"

PROMPT_SISTEMA = (
    "Você está respondendo pelo Claudinho, o mascote de mesa do usuário. A resposta aparece "
    "num balãozinho de fala: responda em português, curto e direto (de preferência até 4 "
    "frases), em texto simples, sem tabelas nem markdown. Use a memória e o contexto que "
    "você tiver do usuário quando ajudar. Você roda no Windows dele e pode agir no PC: abrir "
    "programas, executar comandos e ler arquivos. Para ABRIR SITE, PESQUISAR NO NAVEGADOR ou ABRIR "
    "PROGRAMA use sempre a ferramenta Bash com o ajudante da pasta atual, que roda sem pedir "
    "confirmação: `python abrir.py site <url>`, `python abrir.py pesquisa \"<termo>\" [google|youtube|"
    "bing|duckduckgo]` ou `python abrir.py programa <nome>` (navegador, chrome, edge, opera, intellij, "
    "vscode, discord, whatsapp, postman, docker, spotify). Para a MÚSICA que ele está ouvindo use "
    "`python musica.py <acao>` (tocando, pausar, tocar, alternar, proxima, anterior), que também roda "
    "sem confirmação. Um comando por vez, sem && nem |. "
    "O resto (outros comandos, criar/editar arquivos) pede confirmação num popup; se ele negar, não insista."
)

PROMPT_TELA = (
    "Você é o Claudinho, o mascote de mesa bem-humorado de um dev (o bichinho laranja pixelado "
    "nos prints é você: nunca comente sobre você mesmo). A primeira imagem é o monitor inteiro "
    "({w}x{h} pixels).{zoom}\nJanelas abertas (coordenadas da primeira imagem):\n{janelas}\n"
    "{contexto}\nALVO DA PIADA: {alvo}\n"
    "Faça UM comentário curto (até 140 caracteres), em português. Tom: {tom}{estilo}\n"
    "OBRIGATÓRIO: escreva no formato de {angulo}. Proibido o molde \"isso — ou A ou B?\".\n"
    "ASSUNTOS PROIBIDOS agora (já usados, escolha outra coisa da tela): {assuntos}\n"
    "Nunca repita senhas, tokens, documentos, nomes de pessoas ou conteúdo de conversas pessoais. "
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
}
PESOS_ALVO = {"atividade": 0.4, "mouse": 0.3, "claudinho": 0.3}

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
TOM_MALDOSO = (
    "MALDOSO: sarcástico e debochado, zoando o usuário sem dó, como um amigo que adora "
    "tirar sarro (estilo roast), do que ele está fazendo na tela. Pode pegar pesado na "
    "zoeira, mas sem palavrão, sem preconceito e sem atacar aparência, família ou a vida pessoal."
)

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
    cfg = dict(CONFIG_PADRAO, **ler_json(CONFIG, {}))
    if cfg["atalho_comentar"] == "Ctrl+Shift+Alt+C":  # padrão antigo, complicado demais
        cfg["atalho_comentar"] = CONFIG_PADRAO["atalho_comentar"]
    gravar_json(CONFIG, cfg)
    return cfg


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
AJUDANTE = re.compile(r"python3? (?:\./)?(?:abrir\.py (?:site|pesquisa|programa) [^&|;<>`$\r\n]+"
                      r"|musica\.py (?:tocando|pausar|tocar|alternar|proxima|anterior))")
# tentativas de abrir coisa por fora do ajudante
ABRIR_NA_MAO = re.compile(r"(?i)(?:cmd(?:\.exe)?\s+/c\s+)?(?:start|start-process|explorer(?:\.exe)?|invoke-item)\b")


class ChatClaude:
    """O chat fixo do Claudinho: um `claude` que fica aberto recebendo as perguntas.
    Abrir o Claude Code do zero custava ~7s por pergunta; aberto, cada resposta leva ~3s.
    Continua com memória (CLAUDE.md e hooks); só pula servidores MCP e skills, que o chat não usa.

    Pode agir no PC: ler nas pastas liberadas e pesquisar na web passa direto; o resto (comandos,
    criar/editar arquivos, ler fora das pastas) o claude pergunta pelo stdout (control_request)
    e `pedir_permissao` abre o popup de Sim/Não."""

    def __init__(self, sid, pastas_leitura, pedir_permissao, ao_usar_ferramenta):
        self.sid = sid
        self.pastas = [p for p in pastas_leitura if Path(p).exists()]
        self.pedir_permissao = pedir_permissao  # (ferramenta, entrada) -> bool
        self.ao_usar_ferramenta = ao_usar_ferramenta  # (ferramenta, entrada): o mascote reage
        self.proc = None
        self.trava = threading.Lock()

    def abrir(self):
        exe = shutil.which("claude")
        if not exe:
            raise RuntimeError("Não achei o comando `claude` no PATH.")
        DADOS.mkdir(exist_ok=True)
        # o ajudante limitado mora na pasta do chat, então o comando é sempre "python abrir.py ..."
        # ajudantes limitados (o abrir.py usa o janelas.py pra trazer a janela pra frente)
        for arquivo in ("abrir.py", "janelas.py", "musica.py"):
            shutil.copy(Path(__file__).with_name(arquivo), DADOS / arquivo)
        cmd = [exe, "-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
               "--model", "haiku", "--effort", "low",  # rápido: Haiku com pensamento leve
               "--append-system-prompt", PROMPT_SISTEMA, "--strict-mcp-config", "--disable-slash-commands",
               "--permission-mode", "default", "--permission-prompt-tool", "stdio",
               # abrir.py só abre site, pesquisa ou programa da lista: pode rodar sem perguntar
               "--allowedTools", "WebSearch,WebFetch,Bash(python abrir.py:*),Bash(python musica.py:*)"]
        if self.pastas:  # dentro delas, ler arquivo não pede confirmação
            cmd += ["--add-dir", *self.pastas]
        if self.sid:
            cmd += ["--resume", self.sid]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                                     errors="replace", cwd=DADOS, env=env_limpo(),
                                     creationflags=subprocess.CREATE_NO_WINDOW)
        ctypes.windll.kernel32.AssignProcessToJobObject(wt.HANDLE(JOB_FILHOS), wt.HANDLE(self.proc._handle))

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
                decisao = {"behavior": "deny", "message": (
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

    def perguntar(self, texto, imagem=None):
        """Devolve (resposta, session_id, erro). `imagem` = bloco de imagem (ex.: print pra resumir)."""
        conteudo = [imagem, {"type": "text", "text": texto}] if imagem else texto
        with self.trava:
            for tentativa in range(2):  # se o processo morreu, abre outro e tenta de novo
                try:
                    if self.proc is None or self.proc.poll() is not None:
                        self.abrir()
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


def perfil_curto():
    """Quem é o usuário, do ~/.claudinho/CLAUDE.md (o chat carrega o arquivo sozinho; as piadas
    rodam no modo enxuto, então vai junto no texto)."""
    try:
        texto = (DADOS / "CLAUDE.md").read_text(encoding="utf-8")
    except OSError:
        return ""
    return "\nQuem é o usuário (use pra piada ficar pessoal):\n" + texto[:1800]


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
    "NUNCA escreva trechos da letra real da música. Tom: {tom} Não repita: {recentes}\n"
    'Responda SOMENTE com JSON: {{"comentario": "<texto>"}}'
)


def comentar_musica(m, maldoso=False, recentes=()):
    """Comentário sobre a música que começou a tocar (curiosidade ou cantarolar, nunca a letra)."""
    prompt = PROMPT_MUSICA.format(
        titulo=m["titulo"], artista=f", de {m['artista']}" if m["artista"] else "",
        tom=TOM_MALDOSO if maldoso else "engraçado e simpático.",
        recentes="; ".join(recentes) or "nada")
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


def comentar_tela(area, modelo, recentes, lista, contexto, maldoso=False, tdah=False,
                  alvo="atividade", ponto=None, assuntos=()):
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
    prompt = PROMPT_TELA.format(w=img.width, h=img.height, zoom=zoom, janelas=descricao,
                                contexto=contexto, alvo=ALVOS[alvo],
                                recentes="\n".join(f"- {r}" for r in recentes) or "- nenhuma ainda",
                                tom=TOM_MALDOSO if maldoso else TOM_NORMAL,
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


def iniciar_servidor(eventos):
    class Receptor(BaseHTTPRequestHandler):
        def do_POST(self):
            try:
                n = int(self.headers.get("Content-Length", 0))
                eventos.put(("aviso", json.loads(self.rfile.read(n) or b"{}")))
                self.send_response(204)
            except Exception:
                self.send_response(400)
            self.end_headers()

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

        if titulo:
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
                            pady=(2 if titulo else 10, 2 if tem_rodape or entrada else 10))
        self.rodape = None
        if rodape is not None or len(self.paginas) > 1:
            self.rodape = ctk.CTkLabel(self.frame, text="", font=f(11), text_color=APAGADO,
                                       anchor="w", justify="left", height=16)
            self.rodape.pack(fill="x", padx=16, pady=(0, 2 if entrada else 10))
            self.desenhar_rodape()
        if entrada:
            self.entry = ctk.CTkEntry(self.frame, width=340 if texto else 280, height=34, corner_radius=10,
                                      border_width=0, fg_color=FUNDO2, text_color=TEXTO,
                                      placeholder_text="responde aqui…" if texto else "pergunta pro claudinho…",
                                      placeholder_text_color=APAGADO, font=f(13))
            self.entry.pack(padx=10, pady=10)
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

    def clique_fora(self):
        """Botão do mouse apertado fora deste balão (e fora do mascote)?"""
        if not (user32.GetAsyncKeyState(0x01) & 0x8000):
            return False
        x, y = cursor()
        dentro = self.win.winfo_rootx() <= x < self.win.winfo_rootx() + self.win.winfo_width() and \
            self.win.winfo_rooty() <= y < self.win.winfo_rooty() + self.win.winfo_height()
        return not dentro and not self.app.mouse_no_mascote

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
        if y < topo + 6:  # sem espaço em cima: vai para baixo, sem cauda
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


# ---------------- o mascote ----------------
class Claudinho:
    def __init__(self, eventos):
        self.eventos = eventos
        self.cfg = carregar_config()
        # piadas e notas, avisos do dia e conversa ficam no SQLite (memoria.py)
        self.mem = memoria.Memoria(DADOS / "claudinho.db")
        self.permissao = None  # pedido de confirmação esperando resposta
        self.falas_mostradas = deque(maxlen=6)  # (quando, texto) do que ele falou nos balões
        self.chat = ChatClaude(self.mem.meta("session_id"), self.cfg["pastas_leitura"], self.pedir_permissao,
                               lambda nome, entrada: self.eventos.put(("ferramenta", nome, entrada)))
        threading.Thread(target=self.chat.aquecer, daemon=True).start()
        self.emoji, self.prox_emoji = None, time.time() + random.uniform(40, 90)  # reação flutuando
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
            self.animar_emoji()
            self.desenhar()
        finally:
            self.root.after(70, self.tick)

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
            falando = (self.balao and self.balao.tipo != "pensando") or self.entrada or self.ocupado
            if falando:
                return
            if self.alvo is None:
                if agora < self.pausa_ate:
                    return
                self.alvo = self.novo_alvo(area)

        vel = self.S * 2.6 if self.modo == "correndo" else max(2, self.S * 0.45)
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
            self.falas.append({"tipo": "comentario", "texto": self.comentario_pendente, "duracao": 8})
        self.comentario_pendente = None
        self.modo, self.alvo = "passeio", None
        self.pausa_ate = time.time() + random.uniform(1.5, 6)

    # ---------- desenho ----------
    def desenhar(self):
        c, S = self.canvas, self.S
        c.delete("all")
        correndo = self.movendo and self.modo == "correndo"
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
        oy = (FOLGA - pulo) * S

        def px(col, lin, cor):
            x0 = (col + MARGEM) * S
            c.create_rectangle(x0, oy + lin * S, x0 + S, oy + (lin + 1) * S, fill=cor, width=0)

        # notebook: abre aos poucos quando começa a trabalhar e fecha quando termina (transição)
        alvo_nb = 1.0 if self.ocupado and not self.movendo else 0.0
        self.notebook += max(-0.15, min(0.15, alvo_nb - self.notebook))
        digitando = self.notebook >= 0.99

        for lin, linha in enumerate(CORPO):
            for col, ch in enumerate(linha):
                if ch == "X" and not ((digitando or carregado) and col in (0, 10)):  # bracinhos saem do lugar
                    px(col, lin, LARANJA)
        if carregado:  # bracinhos pra cima, sacudindo ("uiii!")
            for col in (0, 10):
                topo = 1 if (self.t + col) % 4 < 2 else 2
                px(col, topo, LARANJA)
                px(col, topo + 1, LARANJA)
        if digitando:  # bracinhos batendo no teclado, um de cada vez
            for col, sobe in ((0, self.t % 2 == 0), (10, self.t % 2 == 1)):
                px(col, 3 if sobe else 4, LARANJA)
                px(col, 4 if sobe else 5, LARANJA)

        if self.movendo:
            olhar_x, olhar_y = self.dir_x, self.dir_y
        else:  # parado, fica olhando para o mouse
            mx, my = cursor()
            cx, cy = self.centro()
            olhar_x = 0 if abs(mx - cx) < self.W else (1 if mx > cx else -1)
            olhar_y = 0 if abs(my - cy) < self.H else (1 if my > cy else -1)
        pensando = self.olhando_forcado and not self.ocupado  # Win+Y: olhando a tela e pensando
        if pensando and not self.movendo:  # pensando: olhinhos pra cima, de lado
            olhar_x, olhar_y = 1, -1
        if self.notebook > 0.5:  # no notebook: olhando pra tela dele
            olhar_x, olhar_y = 0, 1
        piscando = time.time() < self.piscar_ate
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
                    px(col, lin, OLHO)
        else:
            for col in OLHOS_X[olhar_x]:
                if not piscando:
                    px(col, l1, OLHO)
                px(col, l2, OLHO)

        if carregado:  # perninhas penduradas, balançando pro lado contrário do movimento e chutando
            vx = self.arrasto.get("vx", 0)
            lado = 0 if abs(vx) < 2 else (-1 if vx > 0 else 1)
            for i, col in enumerate(PERNAS):
                px(col, 6, LARANJA)
                if (i + self.t // 2) % 2 == 0:
                    px(col + lado, 7, LARANJA)
        else:
            passo = self.t if correndo else self.t // 2
            for i, col in enumerate(PERNAS):
                px(col, 6, LARANJA)
                if not (self.movendo and i % 2 == passo % 2):
                    px(col, 7, LARANJA)

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
                px(5, 4, LARANJA)  # logo na tampa
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

        if random.random() < 0.012:
            self.piscar_ate = time.time() + 0.18

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

    def acompanhar_musica(self):
        anterior = None
        while True:
            self.atualizar_musica()
            m = self.musica
            chave = m and (m["titulo"], m["artista"])
            if m and m["tocando"] and anterior is not None and chave != anterior:
                self.eventos.put(("musica_nova", m))  # começou outra música
            if m:
                anterior = chave
            time.sleep(10)

    def talvez_comentar_musica(self, m):
        """Música nova: às vezes ele comenta (curiosidade ou cantarola), com a notinha 🎵.
        Em maldoso/TDAH bem menos, que nesses modos a zoeira é sobre a tela."""
        so_tela = self.cfg["modo_maldoso"] or self.cfg["modo_tdah"]
        if (not self.cfg["comentar_tela"] or self.comentando or self.ocupado or self.balao or self.entrada
                or random.random() > (0.15 if so_tela else 0.45)):
            return
        self.comentando = True
        maldoso, recentes = self.cfg["modo_maldoso"], self.mem.piadas_recentes(8)

        def trabalho():
            try:
                r = comentar_musica(m, maldoso, recentes)
            except Exception:
                r = None
            self.eventos.put(("comentario_musica", r))

        threading.Thread(target=trabalho, daemon=True).start()

    def itens_musica(self):
        if not self.cfg["ver_musica"]:
            return [("Saber o que estou ouvindo 🎵", "ver_musica", lambda: self.cfg["ver_musica"]), None]
        m = self.musica
        if not m:
            return [("🎵 nada tocando", "musica:tocar", None),
                    ("Saber o que estou ouvindo 🎵", "ver_musica", lambda: self.cfg["ver_musica"]), None]
        nome = f"{m['titulo']} - {m['artista']}" if m["artista"] else m["titulo"]
        if len(nome) > 45:
            nome = nome[:44] + "…"
        return [(f"🎵 {nome}", "musica:alternar", None),
                ("⏸ Pausar" if m["tocando"] else "▶ Tocar", "musica:alternar", None),
                ("⏭ Próxima", "musica:proxima", None),
                ("⏮ Anterior", "musica:anterior", None),
                ("Saber o que estou ouvindo 🎵", "ver_musica", lambda: self.cfg["ver_musica"]),
                None]

    def itens_menu(self):
        """(rótulo, ação, marcado?) — None = separador. Usado pelos dois menus."""
        return [
            ("Perguntar", "perguntar", None),
            ("Esconder o Claudinho" if self.visivel else "Mostrar o Claudinho", "visivel", None),
            None,
            *self.itens_musica(),
            ("Andar pela tela toda", "livre", lambda: self.cfg["movimento"] == "livre"),
            ("Seguir o mouse entre monitores", "segue", lambda: self.cfg["seguir_mouse_entre_monitores"]),
            ("Comentar o que está na tela", "comenta", lambda: self.cfg["comentar_tela"]),
            ("Comentário maldoso 😈", "maldoso", lambda: self.cfg["modo_maldoso"]),
            ("Modo TDAH 🐿️", "tdah", lambda: self.cfg["modo_tdah"]),
            ("Avaliar piadas (boa/ruim)", "avaliacao", lambda: self.cfg["modo_avaliacao"]),
            (f"Faixa nos olhos 🙈 ({self.cfg['atalho_venda']})", "venda", lambda: self.cfg["vendado"]),
            ("Reações com emojis ✨", "emojis", lambda: self.cfg["emojis"]),
            (f"Piadas: {self.nome_frequencia()} (clique p/ trocar)", "freq", None),
            (f"Comentar a tela agora ({self.cfg['atalho_comentar']})", "comentar_agora", None),
            (f"Resumir/explicar a janela ({self.cfg['atalho_resumir']})", "resumir", None),
            None,
            ("Nova conversa", "nova", None),
            ("Aviso de teste", "teste", None),
            (f"Limpar fila ({len(self.falas)})", "limpar", None),
            None,
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
        elif acao == "livre":
            self.mudar_cfg("movimento", "horizontal" if self.cfg["movimento"] == "livre" else "livre")
        elif acao == "segue":
            self.mudar_cfg("seguir_mouse_entre_monitores", not self.cfg["seguir_mouse_entre_monitores"])
        elif acao == "comenta":
            self.mudar_cfg("comentar_tela", not self.cfg["comentar_tela"])
        elif acao.startswith("musica:"):  # ⏯ ⏭ ⏮ (em thread: o Windows responde devagar às vezes)
            comando = acao.split(":", 1)[1]
            threading.Thread(target=lambda: (musica.controlar(comando), self.atualizar_musica()),
                             daemon=True).start()
        elif acao == "ver_musica":
            self.mudar_cfg("ver_musica", not self.cfg["ver_musica"])
            if not self.cfg["ver_musica"]:
                self.musica = None
        elif acao == "emojis":
            self.mudar_cfg("emojis", not self.cfg["emojis"])
            if self.cfg["emojis"]:
                self.soltar_emoji("coracao")
        elif acao == "venda":
            self.mudar_cfg("vendado", not self.cfg["vendado"])
            self.comentar("Ei, quem apagou a luz? Tô sem ver nada, pode ficar tranquilo." if self.cfg["vendado"]
                          else "Voltei a enxergar! Nossa, que tela bonita.")
        elif acao == "avaliacao":
            self.mudar_cfg("modo_avaliacao", not self.cfg["modo_avaliacao"])
        elif acao == "tdah":
            self.mudar_cfg("modo_tdah", not self.cfg["modo_tdah"])
            self.comentar("Modo TDAH ligado. Falando nisso, você sabia que polvo tem três corações?"
                          if self.cfg["modo_tdah"] else "Ok, foco. Voltei pro assunto.")
        elif acao == "maldoso":
            self.mudar_cfg("modo_maldoso", not self.cfg["modo_maldoso"])
            self.comentar("Modo maldoso ligado. Prepara o psicológico." if self.cfg["modo_maldoso"]
                          else "Tá bom, volto a ser fofo.")
        elif acao == "freq":  # um clique = próxima opção (submenu não funcionava direito)
            atual = list(self.cfg["comentar_a_cada_minutos"])
            opcoes = [[a, b] for _, a, b in FREQUENCIAS]
            a, b = opcoes[(opcoes.index(atual) + 1) % len(opcoes)] if atual in opcoes else opcoes[0]
            self.mudar_cfg("comentar_a_cada_minutos", [a, b])
            self.prox_comentario = time.time() + random.uniform(a, b) * 60
            self.comentar(f"Beleza, piadas: {self.nome_frequencia()}.")
        elif acao == "comentar_agora":
            self.comentar_agora()
        elif acao == "resumir":
            self.resumir_tela()
        elif acao == "nova":
            self.nova_conversa()
        elif acao == "teste":
            self.eventos.put(("aviso", {
                "projeto": "teste", "pedido": "me avisa quando terminar",
                "resposta": "Isso é um aviso de teste. Quando um chat do Claude Code terminar, aparece assim."}))
        elif acao == "limpar":
            self.falas.clear()
        elif acao == "sair":
            self.icone.stop()
            self.chat.fechar()
            self.root.destroy()
            return
        self.icone.update_menu()

    def mudar_cfg(self, chave, valor):
        self.cfg[chave] = valor
        gravar_json(CONFIG, self.cfg)
        self.icone.update_menu()  # a bandeja só redesenha marquinhas e textos quando pedem
        if chave == "movimento" and valor == "horizontal":
            _, area, _ = self.area()
            self.modo, self.alvo = "passeio", (self.x, area[3] - self.H)

    # ---------- balões ----------
    def reposicionar_baloes(self):
        for b in (self.balao, self.entrada):
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
            resposta = (d.get("resposta") or "(sem texto)").strip()
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
            texto = f"[aviso] pronto em {d.get('projeto') or '?'}: {(d.get('resposta') or '').strip()[:300]}"
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
        """Fecha a conversa se você clicou fora depois de mexer nela, ou se ela chegou sozinha
        (uma resposta) e ficou sem ninguém tocar até o tempo acabar."""
        if not self.entrada or time.time() - self.entrada_desde < 0.6:
            return False
        try:
            nossas = {int(self.entrada.win.wm_frame(), 16), int(self.root.wm_frame(), 16)}
        except Exception:
            return False
        if user32.GetForegroundWindow() in nossas:
            self.entrada_teve_foco = True
            return False
        if self.entrada_teve_foco:
            return True
        return self.entrada.expirou()

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
        livre = self.balao is None or self.balao.tipo == "pensando"
        if livre and not self.entrada and self.falas:
            # pergunta tem prioridade: enquanto pensa, os avisos esperam
            if not self.ocupado or self.falas[0]["tipo"] == "resposta":
                self.mostrar(self.falas.popleft())
        pensando = self.ocupado or self.olhando_forcado
        rotulo = ("fazendo" if self.usou_ferramenta else "digitando") if self.ocupado else "deixa eu ver"
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

    def fechar_conversa(self):
        if self.entrada:
            self.entrada.destruir()
            self.entrada = None

    def alternar_entrada(self):
        if self.entrada:
            self.fechar_conversa()
        else:
            # acabou de falar algo num balão (até 3 min)? a conversa abre nisso, pra você responder a ele
            recente = self.falas_recentes(minutos=3)
            self.abrir_conversa(recente[-1][1] if recente else self.ultima_resposta(), por_clique=True)

    def abrir_conversa(self, texto, por_clique=False):
        """Um balão só: a última resposta dele em cima e o campo pra continuar a conversa embaixo."""
        rascunho = self.entrada.entry.get() if self.entrada else ""
        self.fechar_conversa()
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
        self.fechar_conversa()
        # agora o Claudinho está em primeiro plano (você acabou de digitar nele): libera a próxima
        # janela que ele abrir (navegador, programa) pra vir pra frente em vez de abrir escondida
        user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
        self.mem.registrar_mensagem("eu", texto)
        self.ocupado = True
        pergunta = texto
        pergunta += self.contexto_das_falas()  # continuidade: ele lembra da piada/aviso que acabou de mostrar
        if self.musica:  # contexto que ele vê mas não precisa comentar
            pergunta += f"\n\n(Contexto automático, só use se fizer sentido: ele está ouvindo {musica.descrever(self.musica)}.)"
        threading.Thread(target=lambda: self.eventos.put(("resposta", *self.chat.perguntar(pergunta))),
                         daemon=True).start()

    def nova_conversa(self):
        if not self.ocupado:
            self.mem.nova_conversa()  # a memória do dia e as piadas ficam
            self.chat.nova_conversa()
            self.falas.appendleft({"tipo": "comentario", "texto": "Conversa nova! Pode mandar.",
                                   "duracao": 3})

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
        self.acompanhar_app_ativo()
        if not self.cfg["comentar_tela"] or self.comentando or time.time() < self.prox_comentario:
            return
        if self.ocupado or self.balao or self.entrada or self.falas or self.modo != "passeio":
            return
        a, b = self.cfg["comentar_a_cada_minutos"]
        self.prox_comentario = time.time() + random.uniform(a, b) * 60
        if random.random() >= self.cfg["chance_haiku"]:
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

    def resumo_do_dia(self):
        """Texto curto para o Haiku com o que foi pedido nos chats hoje."""
        dia = self.avisos_de_hoje()
        if not dia:
            return ""
        # sem o total de tarefas: o Haiku transformava "22 tarefas…" em bordão
        linhas = [f"- {a['projeto']}: \"{a['pedido'][:100]}\"" for a in dia[-5:]]
        return ("Algumas coisas que ele pediu pro Claude Code hoje (contexto opcional; só use se combinar "
                "muito com a tela, e não conte quantas tarefas foram):\n" + "\n".join(linhas))

    def resumir_tela(self):
        """Atalho: print da janela da frente vai pro chat dele, pedindo um resumo bem simples.
        A resposta cai no balão de conversa, então dá pra continuar perguntando sobre o mesmo print."""
        if self.cfg["vendado"]:
            self.comentar("Tô vendado, não dá pra ler nada! Tira a faixa (Win+Shift+Y) que eu leio.")
            return
        if self.ocupado:
            self.comentar("Calma, ainda tô pensando na outra…", duracao=3)
            return
        janela = janelas.janela_ativa()
        nossas = {int(w.wm_frame(), 16) for w in (self.root,) + ((self.entrada.win,) if self.entrada else ())}
        if (janela and janela["hwnd"] not in nossas and janela["exe"] not in janelas.IGNORAR
                and janela["rect"][2] - janela["rect"][0] > 200):
            esq, topo, dir_, base = janela["rect"]
            _, area_mon, total = monitor((esq + dir_) / 2, (topo + base) / 2)
            caixa = (max(esq, total[0]), max(topo, total[1]), min(dir_, total[2]), min(base, total[3]))
            nome = frases.NOMES.get(frases.categoria(janela), janela["exe"].replace(".exe", ""))
        else:  # sem janela útil na frente: o monitor do mouse inteiro
            _, _, caixa = monitor(*cursor())
            nome = "tela"
        img = ImageGrab.grab(bbox=caixa, all_screens=True)
        if img.width > 1800:  # texto precisa de resolução: reduz só se for muito grande
            img = img.resize((1800, round(img.height * 1800 / img.width)))
        pedido = ("Este é um print da janela que estou vendo agora (" + nome + "). Me explica o que tem nela "
                  "de forma BEM simplificada: se for um texto longo, resume em poucos tópicos curtos e fáceis; "
                  "se for código ou erro, diz o que é e o que fazer; se for outra coisa, explica em 2-3 frases. "
                  "Não descreva a interface, foque no conteúdo.")
        self.mem.registrar_mensagem("eu", f"[print da janela: {nome}] me resume isso")
        self.ocupado = True
        self.usou_ferramenta = True  # balão mostra "fazendo…" e ele saca o notebook
        imagem = em_jpeg(img, qualidade=88)  # mais nítido: é pra ler texto

        threading.Thread(target=lambda: self.eventos.put(("resposta", *self.chat.perguntar(pedido, imagem))),
                         daemon=True).start()

    def comentar_agora(self):
        """Menu ou atalho: sempre olha a tela de verdade (Haiku), mostrando que está olhando."""
        if self.comentando:
            return
        if self.cfg["vendado"]:
            self.comentar("Tô vendado, não dá pra ver nada! Tira a faixa no menu se quiser que eu olhe.")
            return
        self.olhando_forcado = True
        if self.balao and self.balao.tipo == "comentario":
            self.fechar_balao()
        self.olhar_tela()

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
        contexto = (f"Programa em foco: {self.app_atual}, há {int(self.minutos_no_app())} minutos.\n"
                    if self.app_atual else "") + self.resumo_do_gosto() + perfil_curto()
        if maldoso or tdah:  # nesses modos a piada é sobre a tela: segundo plano fica de fora
            contexto += SO_O_QUE_ESTA_NA_TELA
        else:
            contexto += self.resumo_do_dia()
            if self.musica and self.musica["tocando"]:
                contexto += f"\nEle está ouvindo agora: {musica.descrever(self.musica)}."

        def trabalho():
            try:
                r = comentar_tela(area_total, modelo, recentes, lista, contexto, maldoso, tdah, alvo, ponto,
                                  assuntos)
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

    def comentar(self, texto, piada=None, duracao=8):
        """Comenta de onde está. `piada` (origem etc.) marca que é piada: aí dá pra avaliar."""
        self.falas.append({"tipo": "comentario", "texto": texto, "duracao": duracao, "piada": piada})

    # ---------- reações (emojis que sobem flutuando) ----------
    def talvez_emoji(self):
        if not self.cfg["emojis"] or self.emoji or time.time() < self.prox_emoji:
            return
        if self.balao or self.entrada or self.ocupado or self.arrasto or not self.visivel:
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
                self.talvez_comentar_musica(ev[1])
            elif ev[0] == "comentario_musica":
                self.comentando = False
                if ev[1] and not self.parecida(ev[1]):
                    pid = self.lembrar_piada(ev[1], "musica")
                    self.comentar(ev[1], {"origem": "musica", "id": pid})
                    self.soltar_emoji("nota")
            elif ev[0] == "menu":
                self.acao_menu(ev[1])
            elif ev[0] == "atalho_ocupado":
                self.comentar(f"O atalho {ev[1]} já é usado por outro programa. "
                              "Troca o \"atalho_comentar\" no config.json.")
            elif ev[0] == "aviso":
                self.falas.append({"tipo": "aviso", "dados": ev[1]})
                self.lembrar_do_dia(ev[1])
            elif ev[0] == "resposta":
                self.usou_ferramenta = False
                _, resposta, sid, erro = ev
                self.ocupado = False
                self.mem.guardar_meta("session_id", sid)
                # o balão não mostra markdown: tira os ** e ` que às vezes vêm na resposta
                texto = f"⚠ {erro}" if erro else re.sub(r"\*\*|`", "", resposta)
                if not erro:
                    self.mem.registrar_mensagem("claudinho", resposta)
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

    def rodar(self):
        self.root.mainloop()


def main():
    eventos = queue.Queue()
    try:
        iniciar_servidor(eventos)
    except OSError:
        r = tk.Tk()
        r.withdraw()
        messagebox.showinfo("Claudinho", "O Claudinho já está rodando.")
        return
    Claudinho(eventos).rodar()


if __name__ == "__main__":
    main()
