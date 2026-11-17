"""O escritório no celular: link sorteado + código de 6 dígitos, só a rede local, só as rotas do escritório, e "só
olhar" por padrão."""
import http.cookiejar
import json
import urllib.error
import urllib.parse
import urllib.request

import pytest

import celular

BASE = "http://127.0.0.1:47899"


class Aparelho:
    """Um celular: guarda o cookie da sessão como um navegador."""

    def __init__(self):
        self.abrir = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())).open

    def pedir(self, url, metodo="GET", chave=None, corpo=None, tipo="application/json"):
        req = urllib.request.Request(url, data=corpo, method=metodo, headers={"X-Token": chave or "", "Content-Type": tipo})
        try:
            with self.abrir(req, timeout=5) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")

    def entrar(self, c, codigo):
        url = urllib.parse.urlparse(c.url)
        corpo = urllib.parse.urlencode({"k": c.chave, "codigo": codigo}).encode()
        return self.pedir(f"{BASE}{url.path}/entrar", "POST", corpo=corpo, tipo="application/x-www-form-urlencoded")


@pytest.fixture
def servidor(tmp_path, monkeypatch):
    pagina = tmp_path / "escritorio.html"
    pagina.write_text('<html><script>const TOKEN = "__TOKEN__";</script></html>', encoding="utf-8")
    monkeypatch.setattr(celular, "ip_da_rede", lambda: "127.0.0.1")
    monkeypatch.setattr(celular, "PORTA", 47899)
    c = celular.Celular(pagina, 47821, "token-principal")
    repassados = []
    monkeypatch.setattr(c, "_repassar", lambda metodo, caminho, corpo=None: (repassados.append((metodo, caminho)),
                                                                            (200, b'{"ok": 1}'))[1])
    yield c, repassados
    c.desligar()


def test_desligado_por_padrao(servidor):
    c, _ = servidor
    assert c.estado() == {"ligado": False}


def test_link_sozinho_nao_basta_precisa_do_codigo(servidor):
    c, _ = servidor
    e = c.ligar()
    assert e["ligado"] and len(e["codigo"]) == 6 and e["codigo"].isdigit() and "<svg" in e["qr"]
    cel = Aparelho()
    codigo, html = cel.pedir(e["url"])
    assert codigo == 200 and "código de 6 dígitos" in html and c.chave not in html.split('name="k"')[0]
    assert "window.CELULAR" not in html                         # sem o código: nada do escritório
    assert cel.pedir(BASE + "/api/escritorio", chave=c.chave)[0] == 404   # nem a API
    codigo, html = cel.entrar(c, e["codigo"])
    assert codigo == 200 and 'window.CELULAR = {"acoes": false}' in html   # entrou: a página do escritório
    assert "token-principal" not in html                        # a chave do PC nunca vai pro celular
    assert cel.pedir(BASE + "/api/escritorio", chave=c.chave)[0] == 200
    outro = Aparelho()                                            # outro aparelho: precisa do código também
    assert outro.pedir(BASE + "/api/escritorio", chave=c.chave)[0] == 404


def test_caminho_e_codigo_mudam_toda_vez(servidor):
    c, _ = servidor
    primeiro = c.ligar()
    segundo = c.ligar()
    assert primeiro["url"] != segundo["url"] and urllib.parse.urlparse(primeiro["url"]).path != urllib.parse.urlparse(segundo["url"]).path
    assert Aparelho().pedir(primeiro["url"])[0] in (403, 404)     # o link antigo não abre mais
    assert Aparelho().pedir(BASE + "/m?k=" + c.chave)[0] == 404    # nem um caminho fixo


def test_cinco_codigos_errados_desligam(servidor):
    c, _ = servidor
    e = c.ligar()
    cel = Aparelho()
    errado = "000000" if e["codigo"] != "000000" else "111111"
    for restam in range(celular.MAX_TENTATIVAS - 1, 0, -1):
        codigo, html = cel.entrar(c, errado)
        assert codigo == 200 and f"Restam {restam}" in html
    assert cel.entrar(c, errado)[0] == 403
    import time
    time.sleep(1)
    assert not c.estado()["ligado"]                               # desligou: nem o código certo serve mais


def test_so_as_rotas_do_escritorio_e_so_olhar(servidor):
    c, repassados = servidor
    e = c.ligar(acoes=False)
    cel = Aparelho()
    cel.entrar(c, e["codigo"])
    assert cel.pedir(BASE + "/api/escritorio?visivel=1", chave=c.chave)[0] == 200
    assert cel.pedir(BASE + "/api/estado", chave=c.chave)[0] == 404              # painel: não
    assert cel.pedir(BASE + "/api/acao", "POST", c.chave, b"{}")[0] == 403        # ações do Claudinho: nunca
    assert cel.pedir(BASE + "/api/escritorio/pedido", "POST", c.chave, b"{}")[0] == 403   # só olhar: não responde
    assert repassados == [("GET", "/api/escritorio?visivel=1")]


def test_deixando_responder(servidor):
    c, repassados = servidor
    e = c.ligar(acoes=True)
    cel = Aparelho()
    cel.entrar(c, e["codigo"])
    corpo = json.dumps({"id": "1", "opcao": "Não"}).encode()
    assert cel.pedir(BASE + "/api/escritorio/pedido", "POST", c.chave, corpo)[0] == 200
    assert cel.pedir(BASE + "/api/escritorio/celular", "POST", c.chave, b"{}")[0] == 403   # o celular não se religa
    assert ("POST", "/api/escritorio/pedido") in repassados


def test_regras():
    assert celular.da_rede_local("192.168.1.20") and celular.da_rede_local("10.0.0.5") and celular.da_rede_local("127.0.0.1")
    assert not celular.da_rede_local("8.8.8.8")
    assert celular.rota_permitida("/api/escritorio/ficha?chave=x", "GET", False)
    assert not celular.rota_permitida("/api/escritorio/mensagem", "POST", False)
    assert celular.rota_permitida("/api/escritorio/mensagem", "POST", True)
