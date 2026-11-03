"""WhatsApp próprio do Claudinho: um Edge à parte (perfil isolado em ~/.claudinho/whatsapp-edge) com o WhatsApp Web, que
ele controla pelo protocolo de depuração do Chrome (CDP, só em 127.0.0.1). Você escaneia o QR code uma vez, como num
aparelho conectado; depois a janela fica minimizada e ele lê e abre conversas ali, sem mexer no seu navegador nem na sua tela.

Reaproveita as funções de leitura da extensão (extensao/fundo.js), que são código de página: rodam aqui do mesmo jeito.
Quem decide quando e o que mandar continua sendo o Claudinho (limites, "só quem você já escreveu", seu clique em enviar).
"""
import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

import sistema

URL = "https://web.whatsapp.com/"
PERFIL = sistema.DADOS / "whatsapp-edge"
NOVA_CONVERSA_S = 6        # quanto espera a conversa clicada abrir

# o que sobe pro Claudinho: "entrar" (precisa do QR), "conectado", "caiu" (o Edge fechou), "sem_edge"
ESTADOS = ("desligado", "iniciando", "entrar", "conectado", "caiu", "sem_edge")


def _edge():
    return shutil.which("msedge") or next((str(c) for c in (
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft/Edge/Application/msedge.exe") if c.exists()), None)


def _matar_restos():
    """Fecha qualquer Edge que ainda esteja usando o perfil do WhatsApp dele (sobra de um Claudinho que fechou à força):
    um Edge novo no mesmo perfil entrega a execução ao antigo e ignora a porta de controle nova."""
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | "
                        "Where-Object { $_.CommandLine -like '*whatsapp-edge*' } | "
                        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"],
                       creationflags=subprocess.CREATE_NO_WINDOW, timeout=20)
    except Exception:
        pass


def _porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _funcao_js(nome):
    """O texto de uma função de página do fundo.js (do `function nome(` até o `}` sozinho na linha)."""
    texto = (sistema.BASE / "extensao" / "fundo.js").read_text(encoding="utf-8")
    m = re.search(rf"^(?:async )?function {nome}\(.*?^\}}$", texto, re.S | re.M)
    if not m:
        raise RuntimeError(f"função {nome} não achada na extensão")
    return m.group(0)


# onde clicar: o centro da linha da conversa (já rolada pra dentro da tela). Clique sintético do JS não abre a
# conversa no WhatsApp Web; só o clique de verdade (CDP Input.dispatchMouseEvent), por isso aqui só se acha o ponto
JS_ONDE_CLICAR = r"""(nome) => {
  const lado = document.querySelector("#pane-side");
  if (!lado) return {ok: false, erro: "a lista de conversas não está na tela"};
  let linhas = [...lado.querySelectorAll("[role='row']")];
  if (!linhas.length) linhas = [...lado.querySelectorAll("[role='listitem']")];
  const quero = nome.trim().toLowerCase();
  const alvo = linhas.find(el => {
    const t = el.querySelector("span[title]");
    return t && (t.getAttribute("title") || t.textContent).trim().toLowerCase() === quero;
  });
  if (!alvo) return {ok: false, erro: "essa conversa não está entre as recentes da lista"};
  alvo.scrollIntoView({block: "center"});
  const r = alvo.getBoundingClientRect();
  return {ok: true, x: r.x + r.width / 2, y: r.y + r.height / 2};
}"""

JS_CONTATO = r"""(() => {
  const nome = document.querySelector("#main header span[dir='auto']");
  return nome ? (nome.getAttribute("title") || nome.textContent || "").trim() : "";
})()"""

JS_ESTADO = r"""(() => {
  if (document.querySelector("#pane-side")) return "conectado";
  if (document.querySelector("canvas")) return "entrar";
  return "iniciando";
})()"""

JS_FOCAR_CAMPO = r"""(() => {
  const caixa = document.querySelector("#main footer div[contenteditable='true']");
  if (!caixa) return {ok: false, erro: "nenhuma conversa aberta no WhatsApp"};
  if ((caixa.innerText || "").trim()) return {ok: false, erro: "o campo já tem texto seu", ocupado: true};
  caixa.focus();
  return {ok: true};
})()"""

JS_ENVIAR = r"""(async () => {
  const caixa = document.querySelector("#main footer div[contenteditable='true']");
  if (!caixa) return {ok: false, erro: "nenhuma conversa aberta no WhatsApp"};
  await new Promise(r => setTimeout(r, 300));
  const icone = document.querySelector("#main footer [data-icon='send'], #main footer [data-icon='wds-ic-send-filled']");
  const botao = (icone && icone.closest("button")) ||
    document.querySelector("#main footer button[aria-label='Enviar'], #main footer button[aria-label='Send']");
  if (!botao) return {ok: false, erro: "não achei o botão de enviar: aperta Enter você"};
  botao.click();
  await new Promise(r => setTimeout(r, 600));
  return (caixa.innerText || "").trim() ? {ok: false, erro: "preenchi, mas o envio não foi: aperta Enter você"}
                                        : {ok: true, enviada: true};
})()"""


class WhatsAppProprio:
    def __init__(self, ao_mudar=None, job=None):
        self.ao_mudar = ao_mudar    # chamada (estado) quando muda: o Claudinho avisa "escaneia o QR", etc.
        self.job = job              # job do Windows: o Edge fecha junto com o Claudinho
        self.estado = "desligado"
        self.proc = None
        self.porta = 0
        self.ws = None
        self.id = 0
        self.trava = threading.RLock()
        self.ligado = False
        self.escondido = False
        self.id_janela = None
        self.id_alvo = None
        self.ja_conectou = False

    # ---------- ciclo de vida ----------
    def ligar(self):
        if self.ligado:
            return
        self.ligado = True
        threading.Thread(target=self._vigia, daemon=True).start()

    def desligar(self):
        self.ligado = False
        self._fechar_ws()
        proc, self.proc = self.proc, None
        if proc and proc.poll() is None:
            proc.terminate()
        _matar_restos()
        self._mudou("desligado")

    def pronto(self):
        return self.ligado and self.estado == "conectado"

    def _mudou(self, estado):
        if estado == self.estado:
            return
        self.estado = estado
        if self.ao_mudar:
            try:
                self.ao_mudar(estado)
            except Exception:
                pass

    def _iniciar_edge(self):
        edge = _edge()
        if not edge:
            self._mudou("sem_edge")
            return False
        PERFIL.mkdir(parents=True, exist_ok=True)
        _matar_restos()
        time.sleep(1)   # o perfil precisa ser liberado antes de abrir de novo
        self.porta = _porta_livre()
        self.proc = subprocess.Popen(
            [edge, f"--app={URL}", f"--remote-debugging-port={self.porta}", "--window-size=1000,720",
             f"--user-data-dir={PERFIL}", "--disable-sync", "--no-first-run", "--no-default-browser-check",
             "--disable-features=Translate,CalculateNativeWinOcclusion", "--disable-background-timer-throttling",
             "--disable-renderer-backgrounding", "--disable-backgrounding-occluded-windows"],
            creationflags=subprocess.CREATE_NO_WINDOW)
        if self.job:
            import ctypes
            import ctypes.wintypes as wt
            ctypes.windll.kernel32.AssignProcessToJobObject(wt.HANDLE(self.job), wt.HANDLE(self.proc._handle))
        self.escondido, self.id_janela = False, None
        return True

    def _vigia(self):
        """Mantém o Edge vivo e acompanha em que pé está o WhatsApp (QR, conectado). Janela: aparece pro QR, some depois."""
        while self.ligado:
            try:
                if not self.proc or self.proc.poll() is not None:
                    if self.proc and self.estado == "conectado":
                        self._mudou("caiu")
                    self._fechar_ws()
                    if not self._iniciar_edge():
                        time.sleep(30)
                        continue
                    self._mudou("iniciando")
                novo = self.avaliar(JS_ESTADO, tentar=False)
                if novo == "conectado":
                    if not self.escondido:
                        self.janela("minimized")
                        self.escondido = True
                    self.ja_conectou = True
                    self._mudou("conectado")
                elif novo == "entrar":
                    if self.escondido or self.estado != "entrar":
                        self.janela("normal")
                        self.escondido = False
                    self._mudou("entrar")
                elif novo:
                    self._mudou("iniciando" if not self.ja_conectou else self.estado)
            except Exception:
                self._fechar_ws()
            time.sleep(3)

    # ---------- CDP ----------
    def _fechar_ws(self):
        ws, self.ws = self.ws, None
        if ws:
            try:
                ws.close()
            except Exception:
                pass

    def _conectar(self):
        import websocket
        with urllib.request.urlopen(f"http://127.0.0.1:{self.porta}/json", timeout=3) as r:
            alvos = json.load(r)
        alvo = next((a for a in alvos if a.get("type") == "page" and (a.get("url") or "").startswith(URL)), None)
        if not alvo:
            raise RuntimeError("a página do WhatsApp ainda não abriu")
        self.id_alvo = alvo["id"]
        self.ws = websocket.create_connection(alvo["webSocketDebuggerUrl"], timeout=15, suppress_origin=True)

    def _cdp(self, metodo, params=None):
        with self.trava:
            if not self.ws:
                self._conectar()
            self.id += 1
            meu = self.id
            self.ws.send(json.dumps({"id": meu, "method": metodo, "params": params or {}}))
            while True:
                msg = json.loads(self.ws.recv())
                if msg.get("id") == meu:
                    if "error" in msg:
                        raise RuntimeError(msg["error"].get("message", "erro do navegador"))
                    return msg.get("result", {})

    def avaliar(self, expressao, tentar=True):
        """Roda JS na página do WhatsApp e devolve o valor (promessas esperam)."""
        try:
            r = self._cdp("Runtime.evaluate", {"expression": expressao, "awaitPromise": True, "returnByValue": True})
        except Exception:
            self._fechar_ws()
            if not tentar:
                return None
            raise
        if r.get("exceptionDetails"):
            raise RuntimeError((r["exceptionDetails"].get("exception") or {}).get("description") or "erro na página")
        return (r.get("result") or {}).get("value")

    def chamar(self, js_funcao, *args):
        return self.avaliar(f"({js_funcao})(...{json.dumps(list(args))})")

    def janela(self, estado):
        """"normal" (na tela, pro QR) ou "minimized" (escondida). Escondida NÃO é minimizada: minimizada a página fica
        "oculta" e o WhatsApp Web só carrega a última mensagem de cada conversa; fora da tela ela segue "visível"
        e carrega tudo."""
        try:
            if self.id_janela is None:
                self.id_janela = self._cdp("Browser.getWindowForTarget", {"targetId": self.id_alvo})["windowId"]
            self._cdp("Browser.setWindowBounds", {"windowId": self.id_janela, "bounds": {"windowState": "normal"}})
            esquerda = 80 if estado == "normal" else -30000
            self._cdp("Browser.setWindowBounds", {"windowId": self.id_janela,
                                                  "bounds": {"left": esquerda, "top": 60, "width": 1000, "height": 720}})
        except Exception:
            self.id_janela = None

    def mostrar(self, mostrar=True):
        self.janela("normal" if mostrar else "minimized")
        self.escondido = not mostrar

    # ---------- o que o Claudinho usa (mesmo formato da extensão) ----------
    def ler_conversa(self, n=20):
        return self.chamar(_funcao_js("lerWhatsapp"), int(n))

    def ler_lista(self, n=30, todas=False):
        return self.chamar(_funcao_js("lerListaWhatsapp"), int(n), bool(todas))

    def abrir_conversa(self, nome):
        """Clica na conversa (entre as recentes da lista) e espera ela abrir. {"ok"} ou {"ok": False, "erro"}."""
        if not nome:
            return {"ok": False, "erro": "sem nome de contato"}
        from habilidades import mesmo_contato
        if mesmo_contato(self.avaliar(JS_CONTATO), nome):
            return {"ok": True}
        r = self.chamar(JS_ONDE_CLICAR, nome)
        if not (r or {}).get("ok"):
            return r or {"ok": False, "erro": "não consegui abrir"}
        time.sleep(0.2)   # a rolagem assenta antes do clique
        r = self.chamar(JS_ONDE_CLICAR, nome)   # de novo: o ponto muda se a lista rolou
        for tipo, extra in (("mouseMoved", {}), ("mousePressed", {"button": "left", "clickCount": 1}),
                            ("mouseReleased", {"button": "left", "clickCount": 1})):
            self._cdp("Input.dispatchMouseEvent", {"type": tipo, "x": r["x"], "y": r["y"], **extra})
        fim = time.time() + NOVA_CONVERSA_S
        while time.time() < fim:
            if mesmo_contato(self.avaliar(JS_CONTATO), nome):
                self._esperar_mensagens()
                return {"ok": True}
            time.sleep(0.3)
        return {"ok": False, "erro": "a conversa não abriu a tempo"}

    def _esperar_mensagens(self, limite=6):
        """As mensagens carregam depois do cabeçalho (e de pouco em pouco): espera a quantidade parar de crescer."""
        fim, antes, estavel = time.time() + limite, -1, 0
        while time.time() < fim:
            n = self.avaliar("document.querySelectorAll('#main [data-id]').length") or 0
            estavel = estavel + 1 if (n == antes and n > 0) else 0
            if estavel >= 2:
                return
            antes = n
            time.sleep(0.5)

    def escrever(self, texto, enviar=False):
        """Põe o texto no campo (digitação de verdade, pelo CDP: funciona com a janela minimizada) e, se `enviar`, manda."""
        r = self.avaliar(JS_FOCAR_CAMPO)
        if not (r or {}).get("ok"):
            return r
        self._cdp("Input.insertText", {"text": texto})
        if not enviar:
            return {"ok": True, "enviada": False}
        return self.avaliar(JS_ENVIAR)
