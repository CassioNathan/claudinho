"""Abrir o escritório (ClaudCorp) no celular: um mini servidor na rede de casa, ligado só quando você quer.

Segurança (o escritório deixa aprovar permissão e mandar mensagem pros chats, então isso importa):
- desligado por padrão; liga pela aba "📱 Celular" e desliga sozinho em DURACAO_S (ou no botão);
- escuta só no IP da rede local do PC (não em 0.0.0.0) e só atende endereço de rede privada (o seu Wi-Fi);
- cada vez que liga, um caminho e uma chave novos e aleatórios (vão no QR code) e um código de 6 dígitos que só
  aparece na tela do PC: sem o código, o celular não vê nada. Acertou: aquele aparelho ganha uma sessão (cookie);
  outro aparelho digita de novo. 5 códigos errados: desliga na hora (liga de novo = tudo novo);
- só o escritório: a página e uma lista fechada de rotas dele (nada do painel, configuração, ações do Claudinho);
- por padrão só olhar: responder Pode/Não, mandar mensagem e contratar só se você marcar "deixar responder".
É HTTP simples (sem criptografia): use no Wi-Fi de casa/trabalho, não em rede pública.

O mini servidor não mexe em nada sozinho: repassa as rotas permitidas pro servidor principal (127.0.0.1), que faz o
resto como se fosse a janela do escritório no PC.
"""
import ipaddress
import json
import secrets
import socket
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORTA = 47822
DURACAO_S = 2 * 60 * 60
MAX_TENTATIVAS = 5
COOKIE = "claudcorp_sessao"
LEITURA = ("/api/escritorio", "/api/escritorio/ficha")
ACOES = ("/api/escritorio/balao", "/api/escritorio/mensagem", "/api/escritorio/pedido", "/api/escritorio/tarefa")


def ip_da_rede():
    """O IP do PC na rede local (descobre a interface que sai pra rede; não manda nada pela rede)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def da_rede_local(ip):
    try:
        endereco = ipaddress.ip_address(ip)
        return endereco.is_private or endereco.is_loopback
    except ValueError:
        return False


def rota_permitida(caminho, metodo, acoes):
    rota = caminho.split("?")[0]
    if metodo == "GET":
        return rota in LEITURA
    return metodo == "POST" and acoes and rota in ACOES


class Celular:
    def __init__(self, pagina, porta_principal, token_principal):
        self.pagina, self.porta_principal, self.token_principal = pagina, porta_principal, token_principal
        self.servidor, self.chave, self.acoes, self.ate, self.url, self.timer = None, None, False, 0, None, None
        self.caminho, self.codigo, self.sessoes, self.tentativas = None, None, set(), 0
        self.lock = threading.Lock()

    # ---------- ligar / desligar ----------
    def ligar(self, acoes=False):
        self.desligar()
        ip = ip_da_rede()
        if not ip:
            raise RuntimeError("não achei a rede local deste PC (está conectado no Wi-Fi?)")
        self.chave, self.acoes = secrets.token_urlsafe(24), bool(acoes)
        self.caminho = "/" + secrets.token_urlsafe(9)              # o endereço também muda toda vez
        self.codigo = f"{secrets.randbelow(10 ** 6):06d}"          # o segundo passo: só aparece no PC
        self.sessoes, self.tentativas = set(), 0
        self.servidor = ThreadingHTTPServer((ip, PORTA), self._receptor())
        self.servidor.daemon_threads = True
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        self.url = f"http://{ip}:{PORTA}{self.caminho}?k={self.chave}"
        self.ate = time.time() + DURACAO_S
        self.timer = threading.Timer(DURACAO_S, self.desligar)
        self.timer.daemon = True
        self.timer.start()
        return self.estado()

    def desligar(self):
        if self.timer:
            self.timer.cancel()
        if self.servidor:
            servidor, self.servidor = self.servidor, None
            servidor.shutdown()        # (espera fechar: religar abre outro na mesma porta)
            servidor.server_close()
        self.chave, self.url, self.ate, self.timer = None, None, 0, None
        self.caminho, self.codigo, self.sessoes, self.tentativas = None, None, set(), 0

    def estado(self):
        if not self.servidor:
            return {"ligado": False}
        qr = ""
        try:
            import segno
            qr = segno.make(self.url, error="m").svg_inline(scale=5, border=2, dark="#1c1b19", light="#ffffff")
        except Exception:
            pass
        return {"ligado": True, "url": self.url, "qr": qr, "ate": self.ate, "acoes": self.acoes, "codigo": self.codigo,
                "aparelhos": len(self.sessoes)}

    def conferir_codigo(self, codigo):
        """(sessão nova, None) se acertou; (None, quantas tentativas restam) se errou. Errou demais: desliga."""
        with self.lock:
            if not self.codigo:
                return None, 0
            if secrets.compare_digest(str(codigo or "").strip(), self.codigo):
                sessao = secrets.token_urlsafe(24)
                self.sessoes.add(sessao)
                return sessao, None
            self.tentativas += 1
            restam = MAX_TENTATIVAS - self.tentativas
        if restam <= 0:   # alguém chutando: desliga tudo (de outra thread: este pedido ainda está respondendo)
            self.chave = None   # (já não abre mais nada) e desliga logo depois de responder este pedido
            t = threading.Timer(0.5, self.desligar)
            t.daemon = True
            t.start()
        return None, max(0, restam)

    def sessao_ok(self, cabecalho_cookie):
        for parte in (cabecalho_cookie or "").split(";"):
            nome, _, valor = parte.strip().partition("=")
            if nome == COOKIE and valor in self.sessoes:
                return True
        return False

    # ---------- o que o celular pode pedir ----------
    def _repassar(self, metodo, caminho, corpo=None):
        rota = caminho.split("?")[0]
        if rota == "/api/escritorio":
            caminho = rota   # (sem o "visivel": o celular olhando não tira o Claudinho da tela do PC)
        req = urllib.request.Request(f"http://127.0.0.1:{self.porta_principal}{caminho}", data=corpo, method=metodo,
                                     headers={"X-Token": self.token_principal, "Content-Type": "application/json",
                                              "X-Celular": "1",
                                              "Host": f"127.0.0.1:{self.porta_principal}"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read()

    def _receptor(self):
        celular = self

        class Receptor(BaseHTTPRequestHandler):
            def responder(self, codigo, corpo=b"", tipo="application/json"):
                self.send_response(codigo)
                self.send_header("Content-Type", tipo + "; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Referrer-Policy", "no-referrer")
                self.end_headers()
                self.wfile.write(corpo)

            def pode(self):
                return da_rede_local(self.client_address[0]) and celular.chave is not None

            def chave_ok(self):
                return (secrets.compare_digest(self.headers.get("X-Token", ""), celular.chave or "")
                        and celular.sessao_ok(self.headers.get("Cookie")))

            def chave_da_url(self):
                from urllib.parse import parse_qs, urlparse
                url = urlparse(self.path)
                k = (parse_qs(url.query).get("k") or [""])[0]
                return url.path == celular.caminho and secrets.compare_digest(k, celular.chave or "")

            def tela_do_codigo(self, aviso=""):
                html = TELA_CODIGO.replace("__AVISO__", aviso).replace("__ACAO__", self.path.split("?")[0] + "/entrar")
                html = html.replace("__K__", (self.path.split("k=", 1) + [""])[1].split("&")[0])
                return self.responder(200, html.encode("utf-8"), "text/html")

            def do_GET(self):
                if not self.pode():
                    return self.responder(403)
                if celular.caminho and self.path.split("?")[0] == celular.caminho:
                    if not self.chave_da_url():
                        return self.responder(403, "link errado ou vencido: gere outro QR code no PC".encode(), "text/plain")
                    if not celular.sessao_ok(self.headers.get("Cookie")):
                        return self.tela_do_codigo()
                    html = celular.pagina.read_text(encoding="utf-8").replace("__TOKEN__", celular.chave)
                    html = html.replace("<script>", "<script>window.CELULAR = " + json.dumps({"acoes": celular.acoes})
                                        + ";", 1)
                    return self.responder(200, html.encode("utf-8"), "text/html")
                if not self.chave_ok() or not rota_permitida(self.path, "GET", celular.acoes):
                    return self.responder(404)
                try:
                    codigo, corpo = celular._repassar("GET", self.path)
                    return self.responder(codigo, corpo)
                except Exception:
                    return self.responder(502)

            def do_POST(self):
                tamanho = min(int(self.headers.get("Content-Length") or 0), 64_000)
                corpo_pedido = self.rfile.read(tamanho)   # (lê antes de responder: recusar sem ler derruba a conexão)
                if (celular.caminho and self.pode() and self.path.split("?")[0] == celular.caminho + "/entrar"):
                    from urllib.parse import parse_qs
                    campos = parse_qs(corpo_pedido.decode("utf-8", "replace"))
                    k = (campos.get("k") or [""])[0]
                    if not secrets.compare_digest(k, celular.chave or ""):
                        return self.responder(403, "link errado ou vencido".encode(), "text/plain")
                    sessao, restam = celular.conferir_codigo((campos.get("codigo") or [""])[0])
                    if not sessao:
                        self.path = f"{celular.caminho or '/'}?k={k}"
                        if not restam:
                            return self.responder(403, "código errado demais: desliguei. Liga de novo no PC.".encode(),
                                                  "text/plain")
                        return self.tela_do_codigo(f"Código errado. Restam {restam} tentativa(s).")
                    self.send_response(303)
                    self.send_header("Set-Cookie", f"{COOKIE}={sessao}; HttpOnly; SameSite=Strict; Path=/")
                    self.send_header("Location", f"{celular.caminho}?k={k}")
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    return
                if not self.pode() or not self.chave_ok() or not rota_permitida(self.path, "POST", celular.acoes):
                    return self.responder(403)
                try:
                    codigo, corpo = celular._repassar("POST", self.path, corpo_pedido)
                    return self.responder(codigo, corpo)
                except Exception:
                    return self.responder(502)

            def log_message(self, *args):
                pass
        return Receptor


TELA_CODIGO = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>ClaudCorp</title>
<style>body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#1c1b19;
color:#ece9e1;font-family:"Segoe UI",system-ui,sans-serif}form{background:#262522;border:1px solid #3d3b36;
border-radius:16px;padding:24px 22px;width:min(320px,88vw);text-align:center}h1{font-size:20px;margin:0 0 6px}
h1 b{color:#d97757}p{color:#9b978d;font-size:13px;margin:0 0 16px}input{width:100%;box-sizing:border-box;
font:700 28px monospace;letter-spacing:8px;text-align:center;padding:10px;border-radius:10px;border:1px solid #4a4741;
background:#2b2a27;color:#ece9e1;outline:none}input:focus{border-color:#d97757}button{margin-top:14px;width:100%;
border:0;border-radius:10px;padding:11px;background:#d97757;color:#fff;font:600 15px "Segoe UI"}
.aviso{color:#ffb08a;font-size:13px;margin-top:12px;min-height:1em}</style></head><body>
<form method="post" action="__ACAO__"><h1>🏢 <b>Claud</b>Corp</h1>
<p>Digite o código de 6 dígitos que aparece na aba 📱 Celular do escritório, no PC.</p>
<input name="codigo" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" autocomplete="one-time-code" autofocus required>
<input type="hidden" name="k" value="__K__"><button>Entrar</button><div class="aviso">__AVISO__</div></form></body></html>"""
