"""Motores de IA do Claudinho: quem responde o chat, faz as piadas olhando a tela e os resumos.

    claude_code  o Claude Code instalado e logado (comando `claude`) — é o que já existia
    api          uma chave da API da Anthropic (SDK oficial `anthropic`): paga por uso, sem Claude Code
    ollama       um modelo local pelo Ollama (127.0.0.1:11434): grátis, mas usa o PC de quem roda
    nenhum       sem IA: o Claudinho segue com banco de frases, música, esquetes…

O claudinho.pyw configura o motor (configurar) e usa `completar` (uma pergunta, uma resposta: piadas,
música, resumos) e `criar_chat` (a conversa do balão). O chat do Claude Code fica no claudinho.pyw (ChatClaude),
porque é um processo que fica aberto; os outros chats moram aqui.
"""
import base64
import json
import re
import os
import shutil
import subprocess
import threading
import time
import urllib.request

import sistema

MOTORES = ("claude_code", "api", "ollama", "nenhum")
MODELOS_API = {"rapido": "claude-haiku-5-5", "esperto": "claude-sonnet-5-5"}
OLLAMA = "http://127.0.0.1:11434"
# modelos locais que o painel oferece: o leve só lê texto; o maior também enxerga o print da tela
MODELOS_OLLAMA = {
    "qwen3:1.7b": {"nome": "Leve", "tamanho": "~1,4 GB", "visao": False},
    "gemma3:4b": {"nome": "Maior", "tamanho": "~3,3 GB", "visao": True},
}

CONFIG = {"motor": "claude_code", "ollama_modelo": "qwen3:1.7b"}  # o claudinho.pyw atualiza


def configurar(motor, ollama_modelo):
    CONFIG.update(motor=motor if motor in MOTORES else "claude_code", ollama_modelo=ollama_modelo)


# ---------- Claude Code (o processo `claude -p`) ----------
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
    sistema.DADOS.mkdir(exist_ok=True)
    if stream:  # entrada em JSON, permite mandar imagem direto na mensagem
        formato = ["--input-format", "stream-json", "--output-format", "stream-json", "--verbose"]
    else:
        formato = ["--output-format", "json"]
    cmd = [exe, "-p", *formato, *extra] + (["--resume", sid] if sid else [])
    env = env_limpo()
    if sem_pensar:  # sem raciocínio estendido: piada não precisa, e caía de ~30s para ~3s
        env["MAX_THINKING_TOKENS"] = "0"
    proc = subprocess.run(cmd, input=texto, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=sistema.DADOS, env=env, timeout=timeout,
                          creationflags=subprocess.CREATE_NO_WINDOW)
    linhas = proc.stdout.strip().splitlines()
    if not linhas:
        raise RuntimeError((proc.stderr or "sem resposta do claude").strip()[-300:])
    return json.loads(linhas[-1])


ENXUTO = ["--setting-sources", "", "--strict-mcp-config", "--disable-slash-commands",
          "--no-session-persistence", "--tools", ""]


def _completar_claude_code(prompt, imagens, esperto, timeout):
    modelo = "sonnet" if esperto else "haiku"
    if imagens:
        mensagem = {"type": "user", "message": {"role": "user", "content": [*imagens, {"type": "text", "text": prompt}]}}
        d = rodar_claude(json.dumps(mensagem) + "\n", ["--model", modelo, *ENXUTO], timeout=timeout, stream=True,
                         sem_pensar=True)
    else:
        d = rodar_claude(prompt, ["--model", modelo, *ENXUTO], timeout=timeout, sem_pensar=True)
    if d.get("is_error"):
        raise RuntimeError(d.get("result") or "erro do Claude Code")
    return d.get("result", "")


# ---------- API da Anthropic (chave guardada criptografada pelo Windows) ----------
def chave_api():
    return sistema.ler_segredo("api_chave")


def _cliente():
    import anthropic  # só carrega quando o motor é a API
    chave = chave_api()
    if not chave:
        raise RuntimeError("falta a chave da API (painel → Sistema → Motor de IA)")
    return anthropic.Anthropic(api_key=chave, timeout=120.0)


def _pedido_api(esperto):
    """Haiku sem pensamento pras coisas rápidas; Sonnet com pensamento leve quando precisa ler direito."""
    if esperto:
        return {"model": MODELOS_API["esperto"], "output_config": {"effort": "low"}}
    return {"model": MODELOS_API["rapido"], "thinking": {"type": "disabled"}, "output_config": {"effort": "low"}}


def _texto_da_resposta(r):
    if r.stop_reason == "refusal":
        raise RuntimeError("o Claude recusou esse pedido")
    return "".join(b.text for b in r.content if b.type == "text").strip()


def _completar_api(prompt, imagens, esperto, max_tokens):
    r = _cliente().messages.create(max_tokens=max_tokens, **_pedido_api(esperto),
                                   messages=[{"role": "user", "content": [*imagens, {"type": "text", "text": prompt}]}])
    return _texto_da_resposta(r)


# ---------- Ollama (modelo local) ----------
_OLLAMA_STATUS = {"visto": 0.0, "rodando": False, "modelos": []}
BAIXANDO = {"modelo": None, "feito": 0, "total": 0, "erro": None}
# o modelo sai da placa de vídeo sozinho depois de 2 min parado (recarregar leva 2-4 s); o contexto pequeno
# evita que o cache de atenção cresça e ocupe mais VRAM
OLLAMA_KEEP_ALIVE = "2m"
OLLAMA_OPCOES = {"num_ctx": 4096}


def _ollama(caminho, corpo=None, timeout=120):
    pedido = urllib.request.Request(OLLAMA + caminho, data=json.dumps(corpo).encode() if corpo is not None else None,
                                    headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(pedido, timeout=timeout).read())


def _ollama_fluxo(caminho, corpo, timeout=300):
    """Como _ollama, mas devolve os pedaços da resposta conforme chegam (uma linha de JSON por pedaço)."""
    pedido = urllib.request.Request(OLLAMA + caminho, data=json.dumps(corpo).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=timeout) as r:
        for linha in r:
            if linha.strip():
                yield json.loads(linha)


_FIM_DE_FRASE = re.compile(r"(?<=[.!?…])\s+")


def frases_completas(buffer, minimo=18):
    """Do texto que já chegou, separa as frases completas (>= `minimo` letras) e devolve o resto ainda incompleto."""
    partes = _FIM_DE_FRASE.split(buffer)
    frases, atual = [], ""
    for parte in partes[:-1]:
        atual = f"{atual} {parte}".strip()
        if len(atual) >= minimo:
            frases.append(atual)
            atual = ""
    return frases, f"{atual} {partes[-1]}".strip()


def ollama_status():
    """O Ollama está rodando? Que modelos tem? (guarda 5 s: o painel pergunta a cada 3 s)"""
    if time.time() - _OLLAMA_STATUS["visto"] > 5:
        try:
            modelos = [m["name"] for m in _ollama("/api/tags", timeout=0.8).get("models", [])]
            _OLLAMA_STATUS.update(rodando=True, modelos=modelos)
        except Exception:
            _OLLAMA_STATUS.update(rodando=False, modelos=[])
        _OLLAMA_STATUS["visto"] = time.time()
    return {"rodando": _OLLAMA_STATUS["rodando"], "modelos": _OLLAMA_STATUS["modelos"],
            "instalado": bool(shutil.which("ollama")), "baixando": dict(BAIXANDO)}


def _tem_modelo(modelo):
    nomes = ollama_status()["modelos"]
    return modelo in nomes or f"{modelo}:latest" in nomes


def baixar_modelo(modelo):
    """Baixa o modelo no Ollama (em segundo plano, com o progresso em BAIXANDO pro painel mostrar)."""
    if BAIXANDO["modelo"]:
        return

    def trabalho():
        BAIXANDO.update(modelo=modelo, feito=0, total=0, erro=None)
        try:
            pedido = urllib.request.Request(OLLAMA + "/api/pull", data=json.dumps({"model": modelo}).encode(),
                                            headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(pedido, timeout=3600) as resposta:
                for linha in resposta:
                    passo = json.loads(linha or b"{}")
                    if passo.get("error"):
                        raise RuntimeError(passo["error"])
                    if passo.get("total"):
                        BAIXANDO.update(feito=passo.get("completed", 0), total=passo["total"])
        except Exception as e:
            BAIXANDO["erro"] = str(e)
        finally:
            BAIXANDO["modelo"] = None
            _OLLAMA_STATUS["visto"] = 0.0  # confere a lista de modelos de novo
    threading.Thread(target=trabalho, daemon=True).start()


def _imagens_ollama(imagens):
    return [b["source"]["data"] for b in imagens if b.get("type") == "image"]


def _completar_ollama(prompt, imagens, max_tokens, timeout):
    modelo = CONFIG["ollama_modelo"]
    mensagem = {"role": "user", "content": prompt}
    if imagens and MODELOS_OLLAMA.get(modelo, {}).get("visao"):
        mensagem["images"] = _imagens_ollama(imagens)
    r = _ollama("/api/chat", {"model": modelo, "messages": [mensagem], "stream": False, "think": False,
                              "keep_alive": OLLAMA_KEEP_ALIVE,
                              "options": {**OLLAMA_OPCOES, "num_predict": max_tokens}}, timeout=timeout)
    return r["message"]["content"].strip()


def tela_cheia():
    """Tem algo em tela cheia na frente (jogo, vídeo)?"""
    try:
        import janelas
        ativa = janelas.janela_ativa()
        if ativa and ativa["exe"] not in janelas.IGNORAR:
            esq, topo, dir_, base = ativa["rect"]
            import ctypes
            u = ctypes.windll.user32
            largura, altura = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
            return (esq <= 0 and topo <= 0 and dir_ - esq >= largura and base - topo >= altura
                    and ativa["exe"] not in ("explorer.exe",))
    except Exception:
        pass
    return False


_DESCARREGADO = {"em_tela_cheia": False}


def liberar_gpu_se_jogo():
    """Modo jogo de verdade: ao entrar em tela cheia, manda o Ollama tirar o modelo da placa de vídeo na hora
    (uma vez por vez em tela cheia), em vez de esperar o keep_alive vencer."""
    if CONFIG["motor"] != "ollama":
        return
    cheia = tela_cheia()
    if cheia and not _DESCARREGADO["em_tela_cheia"]:
        _DESCARREGADO["em_tela_cheia"] = True
        try:
            for m in _ollama("/api/ps", timeout=1.5).get("models", []):
                _ollama("/api/generate", {"model": m["name"], "keep_alive": 0}, timeout=5)
        except Exception:
            pass
    elif not cheia:
        _DESCARREGADO["em_tela_cheia"] = False


def gpu_livre():
    """Modo jogo do modelo local: com algo em tela cheia na frente, ou pouca memória livre na placa de vídeo,
    o Claudinho não roda o modelo (usa o banco de frases)."""
    if tela_cheia():
        return False  # tela cheia (jogo, vídeo): deixa o PC em paz
    livre = _vram_livre_mb()
    precisa = 4000 if MODELOS_OLLAMA.get(CONFIG["ollama_modelo"], {}).get("visao") else 2000
    return livre is None or livre >= precisa


_VRAM = {"visto": 0.0, "livre": None}


def _vram_livre_mb():
    if time.time() - _VRAM["visto"] > 30 and shutil.which("nvidia-smi"):
        try:
            saida = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                                   capture_output=True, text=True, timeout=5,
                                   creationflags=subprocess.CREATE_NO_WINDOW).stdout
            _VRAM["livre"] = int(saida.split()[0])
        except Exception:
            _VRAM["livre"] = None
        _VRAM["visto"] = time.time()
    return _VRAM["livre"]


# ---------- o que o resto do Claudinho usa ----------
def disponivel():
    """(dá pra usar IA agora?, por quê não)"""
    motor = CONFIG["motor"]
    if motor == "claude_code":
        return (True, "") if sistema.claude_instalado() else (False, "o Claude Code não está instalado")
    if motor == "api":
        return (True, "") if chave_api() else (False, "falta a chave da API")
    if motor == "ollama":
        status = ollama_status()
        if not status["rodando"]:
            return False, "o Ollama não está aberto"
        if not _tem_modelo(CONFIG["ollama_modelo"]):
            return False, f"falta baixar o modelo {CONFIG['ollama_modelo']}"
        return True, ""
    return False, "o motor de IA está desligado"


def ve_imagem():
    """O motor atual enxerga o print da tela?"""
    if CONFIG["motor"] == "ollama":
        return bool(MODELOS_OLLAMA.get(CONFIG["ollama_modelo"], {}).get("visao"))
    return CONFIG["motor"] in ("claude_code", "api")


def completar(prompt, imagens=(), esperto=False, max_tokens=600, timeout=180):
    """Uma pergunta, uma resposta (piadas, comentário de música, resumos). Erro vira exceção."""
    motor = CONFIG["motor"]
    imagens = list(imagens) if ve_imagem() else []
    if motor == "claude_code":
        return _completar_claude_code(prompt, imagens, esperto, timeout)
    if motor == "api":
        return _completar_api(prompt, imagens, esperto, max_tokens)
    if motor == "ollama":
        return _completar_ollama(prompt, imagens, max_tokens, timeout)
    raise RuntimeError("sem motor de IA")


# ---------- chats que não são o Claude Code ----------
class ChatSimples:
    """Base dos chats que guardam a conversa em memória (API e Ollama): mesma cara do ChatClaude."""

    def __init__(self, instrucoes, ao_usar_ferramenta=None):
        self.instrucoes = instrucoes  # função: o texto de sistema na hora (personalidade e "Meu Mestre" mudam)
        self.ao_usar_ferramenta = ao_usar_ferramenta or (lambda nome, entrada: None)
        self.mensagens, self.sid, self.pastas = [], None, []
        self.ultimo_uso, self.modelos_usados = time.time(), []
        self.trava = threading.Lock()

    # o resto do Claudinho chama estes; aqui não tem processo pra abrir/fechar
    def aquecer(self):
        pass

    def fechar(self):
        pass

    def dormir_se_parado(self, minutos=10):
        pass

    def trocar_personalidade(self, personalidade):
        pass  # as instruções são lidas na hora de cada pergunta

    def nova_conversa(self):
        with self.trava:
            self.mensagens = []

    def _guardar(self, pergunta, resposta):
        self.mensagens += [{"role": "user", "content": pergunta}, {"role": "assistant", "content": resposta}]
        self.mensagens = self.mensagens[-24:]  # as últimas 12 trocas: o resto fica pro mini cérebro


# ferramentas do chat pela API: os mesmos ajudantes limitados do Claude Code (rodam pelo claudinho-cli)
FERRAMENTAS = [
    {"name": "musica", "description": (
        "Música e vídeo (YouTube Music e YouTube) no PC do usuário. `argumentos` é a lista do que vem depois do "
        "comando, por exemplo [\"buscar\", \"Helena My Chemical Romance\"], [\"banda\", \"Trivium\"], "
        "[\"tocar_id\", \"<id>\"], [\"videos\", \"<termo>\"], [\"assistir\", \"<id>\"], [\"youtube\", \"<termo>\"], "
        "[\"tocando\"], [\"pausar\"], [\"tocar\"], [\"proxima\"], [\"anterior\"], [\"curtir\"], [\"curtidas\"], "
        "[\"player\", \"aleatorio\"], [\"player\", \"volume\", \"40\"], [\"video\", \"velocidade\", \"1.5\"]."),
     "input_schema": {"type": "object", "properties": {"argumentos": {"type": "array", "items": {"type": "string"}}},
                      "required": ["argumentos"], "additionalProperties": False}},
    {"name": "abrir", "description": (
        "Abre no PC do usuário: [\"site\", \"<url>\"], [\"pesquisa\", \"<termo>\", \"google|youtube|bing|duckduckgo\"] "
        "ou [\"programa\", \"<nome>\"] (navegador, chrome, edge, opera, intellij, vscode, discord, whatsapp, "
        "postman, docker, spotify)."),
     "input_schema": {"type": "object", "properties": {"argumentos": {"type": "array", "items": {"type": "string"}}},
                      "required": ["argumentos"], "additionalProperties": False}},
]
ACOES = {"musica": {"tocando", "pausar", "tocar", "alternar", "proxima", "anterior", "curtir", "curtidas", "buscar",
                    "artista", "youtube", "banda", "videos", "tocar_id", "assistir", "player", "video"},
         "abrir": {"site", "pesquisa", "programa"}}


def rodar_ajudante(nome, argumentos):
    """Roda um ajudante limitado (música ou abrir) e devolve o que ele escreveu."""
    if nome not in ACOES or not argumentos or argumentos[0] not in ACOES[nome]:
        return "recusado: ação não permitida"
    r = subprocess.run(sistema.comando_cli(nome, *[str(a)[:300] for a in argumentos]), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=90,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    return ((r.stdout or "") + (r.stderr or "")).strip()[:4000] or "feito"


class ChatAPI(ChatSimples):
    def perguntar(self, texto, imagem=None, modelo=None, ao_frase=None):
        """Devolve (resposta, sid, erro), como o ChatClaude. `modelo="sonnet"` = pergunta que precisa ler direito."""
        self.ultimo_uso = time.time()
        conteudo = ([imagem] if imagem else []) + [{"type": "text", "text": texto}]
        with self.trava:
            try:
                cliente = _cliente()
                # Haiku sem pensamento: a conversa guardada só tem texto, e bloco de pensamento faltando no
                # histórico seria "histórico editado" pra API. O Sonnet (resumo de tela) é uma pergunta só.
                pedido = _pedido_api(modelo == "sonnet")
                conversa = self.mensagens + [{"role": "user", "content": conteudo}]
                ferramentas = FERRAMENTAS + [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}]
                for _ in range(8):  # no máximo 8 idas e voltas de ferramenta
                    r = cliente.messages.create(max_tokens=4000, system=self.instrucoes(), tools=ferramentas,
                                                messages=conversa, **pedido)
                    if r.stop_reason not in ("tool_use", "pause_turn"):
                        break
                    conversa.append({"role": "assistant", "content": r.content})
                    if r.stop_reason == "pause_turn":
                        continue
                    resultados = []
                    for bloco in r.content:
                        if bloco.type == "tool_use":
                            argumentos = (bloco.input or {}).get("argumentos") or []
                            self.ao_usar_ferramenta(bloco.name, {"command": " ".join([bloco.name, *argumentos])})
                            resultados.append({"type": "tool_result", "tool_use_id": bloco.id,
                                               "content": rodar_ajudante(bloco.name, argumentos)})
                    conversa.append({"role": "user", "content": resultados})
                resposta = _texto_da_resposta(r)
                self.modelos_usados = [r.model]
                # na memória da conversa fica só o texto (o print pesaria em todas as perguntas seguintes)
                self._guardar(("[print da tela] " if imagem else "") + texto, resposta)
                return resposta, None, None
            except Exception as e:
                if "authentication_error" in str(e) or "invalid x-api-key" in str(e):
                    return None, None, "A chave da API foi recusada pela Anthropic: confira ela no painel (Sistema → Motor de IA)."
                return None, None, str(e)


class ChatOllama(ChatSimples):
    FLUXO = True   # sabe devolver a resposta frase a frase (ao_frase), pra voz começar a falar logo
    def perguntar(self, texto, imagem=None, modelo=None, ao_frase=None):
        self.ultimo_uso = time.time()
        modelo_local = CONFIG["ollama_modelo"]
        mensagem = {"role": "user", "content": texto}
        if imagem and MODELOS_OLLAMA.get(modelo_local, {}).get("visao"):
            mensagem["images"] = _imagens_ollama([imagem])
        elif imagem:
            mensagem["content"] = "(Ele mandou um print, mas você não enxerga imagens: diga isso.)\n" + texto
        corpo = {"model": modelo_local, "think": False, "keep_alive": OLLAMA_KEEP_ALIVE, "options": OLLAMA_OPCOES,
                 "messages": [{"role": "system", "content": self.instrucoes()}, *self.mensagens, mensagem]}
        with self.trava:
            try:
                if ao_frase:  # em fluxo: cada frase pronta vai pra fala (voz) enquanto o resto ainda está sendo escrito
                    resposta, pendente = "", ""
                    for pedaco in _ollama_fluxo("/api/chat", dict(corpo, stream=True)):
                        novo = pedaco.get("message", {}).get("content", "")
                        resposta += novo
                        frases, pendente = frases_completas(pendente + novo)
                        for frase in frases:
                            ao_frase(frase)
                    if pendente.strip():
                        ao_frase(pendente.strip())
                    resposta = resposta.strip()
                else:
                    r = _ollama("/api/chat", dict(corpo, stream=False), timeout=300)
                    resposta = r["message"]["content"].strip()
                self.modelos_usados = [modelo_local]
                self._guardar(texto, resposta)
                return resposta, None, None
            except Exception as e:
                return None, None, f"o modelo local não respondeu ({e})"


class ChatNenhum(ChatSimples):
    def perguntar(self, texto, imagem=None, modelo=None, ao_frase=None):
        return None, None, ("Estou sem motor de IA, então não consigo conversar. Escolha um no painel "
                            "(Sistema → Motor de IA): Claude Code, chave da API ou um modelo local.")
