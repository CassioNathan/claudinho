"""Ficha de cada programa (e de cada site, no navegador): o que é e o que você costuma fazer nele.

Sem ela, o comentário só tinha o print e o nome do .exe, e ele "interpretava a tela" (no jogo, piada sobre o menu).
Com ela, ele já sabe que é um jogo, uma pedaleira, o sistema do trabalho, antes de olhar.

Custo: cada programa ou site ganha a ficha UMA vez. Primeiro o que é de graça (o que o próprio .exe diz de si,
a pasta onde está, as categorias que o Claudinho já conhece); depois o modelo leve local completa, se puder.
Se mesmo assim sair genérica ("um site pra navegar na internet"), ele pesquisa UMA vez, de graça e sem IA: a página
inicial do próprio site (título e descrição) ou, pra programa, a Wikipédia. O leve resume o que achou.
Nunca vai pra nuvem: sem o local (jogo na frente, placa ocupada, Ollama fechado), a ficha fica só com o básico e
ele tenta de novo mais tarde. Fica em ~/.claudinho/fichas.json; o painel mostra, corrige e apaga.
"""
import ctypes
import ctypes.wintypes as wt
import html
import json
import re
import threading
import time
import urllib.parse
import urllib.request

import frases
import sistema

ARQUIVO = sistema.DADOS / "fichas.json"
CATEGORIAS = ("jogo", "navegador", "trabalho", "programacao", "musica", "video", "conversa", "criacao", "sistema", "outro")
SIGNIFICADO = {"sistema": "pastas e configurações do Windows", "trabalho": "sistemas e sites de empresa, escritório",
               "criacao": "design, edição, desenho"}   # sem isso o leve chama o "sistema de gestão" de "sistema"
COMENTAR = ("sim", "pouco", "nao")   # "pouco": só sobre o que você está fazendo, nada de narrar a interface
TENTAR_DE_NOVO = 30 * 60             # ficha só com o básico: o local tenta completar de novo depois disso
PASTAS_DE_JOGO = re.compile(r"(?i)\\(steamapps\\common|epic games|riot games|gog galaxy\\games|xboxgames|"
                            r"battle\.net|ubisoft game launcher\\games|ea games|origin games)\\")
# o que o Claudinho já conhecia (frases.PROGRAMAS) -> categoria da ficha
DE_FRASES = {"ide": "programacao", "delphi": "programacao", "vscode": "programacao", "terminal": "programacao",
             "banco": "programacao", "postman": "programacao", "docker": "programacao", "claude": "programacao",
             "discord": "conversa", "whatsapp": "conversa", "reuniao": "conversa", "navegador": "navegador",
             "planilha": "trabalho", "notion": "trabalho", "suporte": "trabalho", "musica": "musica",
             "pastas": "sistema", "youtube": "video", "streaming": "video", "github": "programacao",
             "stackoverflow": "programacao", "localhost": "programacao", "chatgpt": "trabalho", "email": "trabalho",
             "linkedin": "trabalho", "redes": "conversa", "tarefas": "trabalho"}

_trava = threading.Lock()
_gerando = set()


def ler():
    try:
        dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {}
    except Exception:
        return {}


def gravar(fichas):
    ARQUIVO.parent.mkdir(exist_ok=True)
    tmp = ARQUIVO.with_suffix(".tmp")
    tmp.write_text(json.dumps(fichas, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(ARQUIVO)


def eh_navegador(exe):
    return frases.PROGRAMAS.get(exe) == "navegador"


def chave(exe, site=""):
    """'site:youtube.com' no navegador (quando a extensão disse o site), senão 'exe:jogo.exe'."""
    site = (site or "").lower().removeprefix("www.")
    return f"site:{site}" if eh_navegador(exe) and site else f"exe:{exe}"


# ---------- o que o .exe diz de si (de graça) ----------
def caminho_do_processo(hwnd):
    pid = wt.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    k = ctypes.windll.kernel32
    k.OpenProcess.restype = wt.HANDLE
    h = k.OpenProcess(0x1000, False, pid.value)
    if not h:
        return ""
    try:
        buf, n = ctypes.create_unicode_buffer(520), wt.DWORD(520)
        return buf.value if k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)) else ""
    finally:
        k.CloseHandle(h)


def info_do_exe(caminho):
    """{produto, descricao, empresa} da versão do arquivo (o que aparece em Propriedades → Detalhes)."""
    v = ctypes.windll.version
    tam = v.GetFileVersionInfoSizeW(caminho, None)
    if not tam:
        return {}
    buf = ctypes.create_string_buffer(tam)
    if not v.GetFileVersionInfoW(caminho, 0, tam, buf):
        return {}
    p, n = ctypes.c_void_p(), wt.UINT()
    idiomas = ["040904b0", "041604b0", "000004b0", "040904e4"]
    if v.VerQueryValueW(buf, "\\VarFileInfo\\Translation", ctypes.byref(p), ctypes.byref(n)) and n.value >= 4:
        lang, cp = ctypes.cast(p, ctypes.POINTER(wt.WORD))[0:2]
        idiomas.insert(0, f"{lang:04x}{cp:04x}")
    info = {}
    for campo, nome in (("ProductName", "produto"), ("FileDescription", "descricao"), ("CompanyName", "empresa")):
        for idioma in idiomas:
            if v.VerQueryValueW(buf, f"\\StringFileInfo\\{idioma}\\{campo}", ctypes.byref(p), ctypes.byref(n)) and n.value:
                texto = ctypes.wstring_at(p, n.value).strip("\x00 ").strip()
                if texto:
                    info[nome] = texto[:80]
                    break
    return info


def basica(exe, caminho="", info=None, site="", titulo=""):
    """A ficha sem IA: nome e categoria pelo que já se sabe."""
    info = info or {}
    if site:
        cat = DE_FRASES.get(frases.categoria({"exe": exe, "titulo": f"{titulo} {site}"}), "outro")
        cat = "outro" if cat == "navegador" else cat   # um site não é "o navegador": o local diz o que é
        nome = site
    else:
        cat = DE_FRASES.get(frases.PROGRAMAS.get(exe, ""), "outro")
        if cat == "outro" and PASTAS_DE_JOGO.search(caminho or ""):
            cat = "jogo"
        nome = info.get("produto") or info.get("descricao") or re.sub(r"(?i)\.exe$", "", exe)
    return {"nome": nome[:60], "categoria": cat, "o_que_e": info.get("descricao", "") if not site else "",
            "faz": "", "comentar": "pouco" if cat == "jogo" else "sim", "origem": "basica", "quando": time.time()}


PROMPT = """Você classifica um {tipo} do computador de uma pessoa, pra um mascote que comenta o que ela faz.
Dados:
{dados}
Responda só um JSON em português do Brasil, com "categoria" (uma de: {categorias}), "o_que_e" (o que é, até 12
palavras) e "faz" (o que a pessoa costuma fazer nele, até 10 palavras). Exemplo, pro cs2.exe:
{{"categoria": "jogo", "o_que_e": "jogo de tiro competitivo online da Valve", "faz": "jogando partidas competitivas"}}
Se não conhecer, deduza pelo nome e pela empresa e seja vago; não invente detalhes."""


# ---------- pesquisa (só quando a ficha sai genérica) ----------
VAGA = re.compile(r"(?i)naveg|internet|programa de computador|desconhecid|não sei|não conhe|^(um |o )?(software|aplicativo|programa|site)$")
NAVEGADOR_FALSO = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def generica(ficha):
    """A ficha não diz nada que ajude a comentar?"""
    o_que_e = (ficha or {}).get("o_que_e", "").strip()
    return not ficha or ficha.get("categoria") == "outro" or not o_que_e or bool(VAGA.search(o_que_e))


def _baixar(url, limite=300_000, timeout=8):
    r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": NAVEGADOR_FALSO}), timeout=timeout)
    bruto = r.read(limite)
    charset = r.headers.get_content_charset()
    if not charset:
        m = re.search(rb"""(?i)<meta[^>]+charset=["']?([\w-]+)""", bruto[:4000])
        charset = m.group(1).decode() if m else "utf-8"
    try:
        return bruto.decode(charset, "replace")
    except LookupError:
        return bruto.decode("utf-8", "replace")


def _meta(pagina, nome):
    for m in re.finditer(r"(?is)<meta\b[^>]*>", pagina):
        tag = m.group(0)
        if re.search(rf"""(?i)(name|property)\s*=\s*["']{re.escape(nome)}["']""", tag):
            c = re.search(r"""(?is)content\s*=\s*("([^"]*)"|'([^']*)')""", tag)
            if c:
                return html.unescape(c.group(2) if c.group(2) is not None else c.group(3)).strip()
    return ""


def dominio_raiz(site):
    """portal.empresa.com.br -> empresa.com.br (pra quando o subdomínio não tem página inicial)."""
    partes = site.split(".")
    n = 3 if len(partes) >= 3 and len(partes[-1]) == 2 and partes[-2] in ("com", "net", "org", "gov", "edu", "co") else 2
    return ".".join(partes[-n:])


def pesquisar_site(site):
    """{nome, texto} da página inicial do site (título e descrição que ele mesmo dá), ou {}."""
    for alvo in dict.fromkeys((site, dominio_raiz(site))):
        try:
            pagina = _baixar(f"https://{alvo}/")
        except Exception:
            continue
        t = re.search(r"(?is)<title[^>]*>(.*?)</title>", pagina)
        titulo = re.sub(r"\s+", " ", html.unescape(t.group(1))).strip() if t else ""
        descricao = _meta(pagina, "description") or _meta(pagina, "og:description")
        if titulo or descricao:
            return {"nome": _meta(pagina, "og:site_name")[:60],
                    "texto": "; ".join(x for x in (titulo[:120], descricao[:300]) if x)}
    return {}


def pesquisar_programa(nome, empresa=""):
    """Resumo da Wikipédia (português, senão inglês) sobre o programa, ou ""."""
    busca = nome if not empresa or empresa.lower() in nome.lower() else f"{nome} {empresa}"
    for lingua in ("pt", "en"):
        try:
            url = (f"https://{lingua}.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit=1"
                   f"&srsearch={urllib.parse.quote(busca)}")
            achados = json.loads(_baixar(url, timeout=6))["query"]["search"]
        except Exception:
            continue
        palavras = {w for w in re.findall(r"\w{3,}", busca.lower())}
        if achados and palavras & set(re.findall(r"\w{3,}", achados[0]["title"].lower())):   # o artigo é dele mesmo
            trecho = html.unescape(re.sub(r"<[^>]+>", "", achados[0].get("snippet", "")))
            return f"{achados[0]['title']}: {trecho}"[:400]
    return ""


def completar_com_local(ficha, exe, info, site="", titulo="", pesquisa=""):
    """O modelo leve local melhora a ficha básica. Devolve a ficha nova ou None (local indisponível ou resposta ruim)."""
    import motores
    import revisao
    dados = [f"- executável: {exe}"] + [f"- {k}: {v}" for k, v in (info or {}).items()]
    if site:
        dados = [f"- site: {site}"]   # sem o título da aba: a ficha é do site, não do vídeo/página de agora
    elif titulo:
        dados.append(f"- título da janela: {titulo[:80]}")
    if pesquisa:
        dados.append(f"- achado na internet (pode não ser exatamente ele): {pesquisa}")
    if ficha["categoria"] != "outro":
        dados.append(f"- categoria provável: {ficha['categoria']}")
    resposta = motores.so_local(PROMPT.format(tipo="site" if site else "programa", dados="\n".join(dados),
                                              categorias=", ".join(f"{c} ({SIGNIFICADO[c]})" if c in SIGNIFICADO else c
                                                                   for c in CATEGORIAS)),
                               max_tokens=160, timeout=60)
    r = revisao.extrair_json(resposta or "")
    if not r:
        return None
    nova = dict(ficha)
    for campo, limite in (("o_que_e", 120), ("faz", 120)):   # o nome vem do .exe ou do site: o leve estraga
        valor = str(r.get(campo) or "").strip()
        if valor and not re.search(r"(?i)\bat[ée] \d+ palavras|em at[ée]|o que (a pessoa|é)\b|comentando", valor):   # o leve às vezes devolve o enunciado
            nova[campo] = valor[:limite]
    cat = str(r.get("categoria") or "").strip().lower()
    if cat in CATEGORIAS and ficha["categoria"] in ("outro", "navegador"):   # a categoria sem IA, quando há, vale mais
        nova["categoria"] = cat
    if nova["categoria"] == "jogo" and ficha["categoria"] != "jogo":
        nova["comentar"] = "pouco"
    nova.update(origem="local", quando=time.time())
    return nova


# ---------- uso ----------
def buscar(exe, site=""):
    return ler().get(chave(exe, site))


def garantir(janela, site="", titulo_aba=""):
    """Cria (ou completa) a ficha da janela em segundo plano. Barato de chamar sempre: se já tem ficha boa, não faz nada."""
    exe = (janela or {}).get("exe", "")
    if not exe or (eh_navegador(exe) and not site):
        return
    k = chave(exe, site)
    atual = ler().get(k)
    if atual and (atual.get("origem") != "basica" or time.time() - atual.get("quando", 0) < TENTAR_DE_NOVO):
        return
    with _trava:
        if k in _gerando:
            return
        _gerando.add(k)
    threading.Thread(target=_gerar, args=(k, janela, site, titulo_aba, atual), daemon=True).start()


def _gerar(k, janela, site, titulo_aba, atual):
    try:
        exe = janela["exe"]
        caminho, info = "", {}
        if not site:
            try:
                caminho = caminho_do_processo(janela["hwnd"])
                info = info_do_exe(caminho) if caminho else {}
            except Exception:
                pass
        titulo = titulo_aba or janela.get("titulo", "")
        ficha = atual or basica(exe, caminho, info, site, titulo)
        nova = completar_com_local(ficha, exe, info, site, titulo, ficha.get("pesquisa", ""))
        if generica(nova or ficha) and "pesquisa" not in ficha:   # ainda vaga: pesquisa uma vez (guarda pra não repetir)
            if site:
                achado = pesquisar_site(site)
                ficha = dict(ficha, pesquisa=achado.get("texto", ""), nome=achado.get("nome") or ficha["nome"])
            else:
                ficha = dict(ficha, pesquisa=pesquisar_programa(info.get("produto") or ficha["nome"], info.get("empresa", "")))
            if ficha["pesquisa"]:
                nova = completar_com_local(ficha, exe, info, site, titulo, ficha["pesquisa"])
                if not nova and generica(ficha):   # sem o local agora: a descrição achada já serve
                    ficha["o_que_e"] = ficha["pesquisa"].split("; ")[-1][:120]
        with _trava:
            fichas = ler()
            if fichas.get(k, {}).get("origem") == "voce":   # você corrigiu no meio do caminho: vale a sua
                return
            fichas[k] = nova or dict(ficha, quando=time.time())
            gravar(fichas)
    except Exception:
        pass
    finally:
        with _trava:
            _gerando.discard(k)


def contexto(ficha):
    """A ficha em uma linha pro prompt do comentário."""
    if not ficha:
        return ""
    partes = [f"{ficha['nome']} ({ficha['categoria']})"]
    if ficha.get("o_que_e"):
        partes.append(ficha["o_que_e"])
    if ficha.get("faz"):
        partes.append(f"normalmente ele está {ficha['faz']}" if ficha.get("origem") == "voce"
                      else f"provavelmente: {ficha['faz']}")
    texto = "O que ele está usando: " + "; ".join(partes) + "."
    if ficha.get("comentar") == "pouco" or ficha["categoria"] == "jogo":
        texto += (" Comente sobre o que ELE está fazendo ali (a partida, o trabalho), nunca descreva a interface, "
                  "menus ou elementos da tela.")
    return texto + "\n"


def pode_comentar(ficha):
    return not ficha or ficha.get("comentar") != "nao"


# ---------- painel ----------
def listar():
    return [dict(f, chave=k) for k, f in sorted(ler().items(), key=lambda kv: -kv[1].get("quando", 0))]


def corrigir(k, campos):
    with _trava:
        fichas = ler()
        if k not in fichas:
            return False
        f = fichas[k]
        for campo in ("nome", "o_que_e", "faz"):
            if campo in campos:
                f[campo] = str(campos[campo]).strip()[:120]
        if campos.get("categoria") in CATEGORIAS:
            f["categoria"] = campos["categoria"]
        if campos.get("comentar") in COMENTAR:
            f["comentar"] = campos["comentar"]
        f.update(origem="voce", quando=time.time())
        gravar(fichas)
        return True


def apagar(k):
    with _trava:
        fichas = ler()
        if fichas.pop(k, None) is None:
            return False
        gravar(fichas)
        return True

