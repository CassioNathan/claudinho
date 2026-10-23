"""O que está tocando no PC e controle do player, pelos controles de mídia do Windows
(os mesmos do controle de volume): vale pra Spotify, YouTube no navegador, YouTube Music etc.

Também é um ajudante limitado do chat, que roda sem confirmação:
    python musica.py tocando      mostra o que está tocando
    python musica.py pausar       pausa
    python musica.py tocar        volta a tocar
    python musica.py alternar     pausa/toca
    python musica.py proxima      pula pra próxima
    python musica.py anterior     volta pra anterior
    python musica.py buscar "<música e/ou artista>"   toca no YouTube Music (e segue num rádio parecido)
    python musica.py artista "<artista>"              toca o mais ouvido do artista (e segue no rádio dele)
    python musica.py youtube "<o que procurar>"       abre no YouTube o primeiro vídeo da pesquisa
    python musica.py curtir                           curte a música que está tocando no YouTube Music
    python musica.py banda "<banda>"                  lista as músicas mais ouvidas e os álbuns (com id)
    python musica.py tocar_id <id>                    toca no YouTube Music a música desse id (da lista)
    python musica.py curtidas                         toca as músicas que você curtiu
    python musica.py player <acao> [valor]            pausar, tocar, proxima, anterior, aleatorio, repetir, volume 0-100
    python musica.py videos "<o que procurar>"        lista os vídeos da pesquisa do YouTube (com id)
    python musica.py assistir <id>                    abre esse vídeo do YouTube numa aba nova, na frente
    python musica.py video <acao> [valor]             pausar, tocar, velocidade 0.5-2, avancar N, voltar N, legenda, cinema

Buscar e tocar usa o YouTube Music sem login (ytmusicapi) só pra achar a música; quem toca é o seu
navegador, logado na sua conta. Com a extensão do Claudinho instalada, usa a aba que já está aberta;
sem ela (ou sem aba aberta), abre uma nova. Pausa o que estiver tocando pra não sair duas músicas.
"""
import asyncio
import os
import sys
import time
import webbrowser
from pathlib import Path

import sistema

from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as Gerenciador,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as Status,
)

APPS = {"spotify": "Spotify", "opera": "Opera", "chrome": "Chrome", "msedge": "Edge",
        "firefox": "Firefox", "brave": "Brave", "deezer": "Deezer", "zunemusic": "Media Player"}


def nome_do_app(app_id):
    baixo = (app_id or "").lower()
    return next((nome for chave, nome in APPS.items() if chave in baixo), Path(app_id or "?").stem)


async def _sessao():
    gerenciador = await Gerenciador.request_async()
    return gerenciador.get_current_session()


async def _tocando():
    sessao = await _sessao()
    if sessao is None:
        return None
    info = await sessao.try_get_media_properties_async()
    status = sessao.get_playback_info().playback_status
    if not info or not info.title:
        return None
    return {"titulo": info.title, "artista": info.artist or "", "app": nome_do_app(sessao.source_app_user_model_id),
            "tocando": status == Status.PLAYING}


async def _controlar(acao):
    sessao = await _sessao()
    if sessao is None:
        return False
    metodo = {"pausar": sessao.try_pause_async, "tocar": sessao.try_play_async,
              "alternar": sessao.try_toggle_play_pause_async, "proxima": sessao.try_skip_next_async,
              "anterior": sessao.try_skip_previous_async}[acao]
    return bool(await metodo())


def tocando():
    """{'titulo', 'artista', 'app', 'tocando'} ou None se nada estiver tocando/pausado."""
    try:
        return asyncio.run(_tocando())
    except Exception:
        return None


def controlar(acao):
    try:
        return asyncio.run(_controlar(acao))
    except Exception:
        return False


def buscar(termo, artista=False):
    """A música que o YouTube Music acha pro termo: {'id', 'titulo', 'artista'} ou None.
    Com `artista=True`, o termo é um artista: pega a música mais ouvida dele."""
    from ytmusicapi import YTMusic  # só carrega quando precisa (é mais pesadinho)
    yt = YTMusic()
    if artista:
        achados = yt.search(termo, filter="artists", limit=1)
        if achados:
            dados = yt.get_artist(achados[0]["browseId"])
            musicas = (dados.get("songs") or {}).get("results") or []
            if musicas:
                m = musicas[0]
                return {"id": m["videoId"], "titulo": m["title"],
                        "artista": ", ".join(a["name"] for a in m.get("artists") or []) or dados.get("name", "")}
    for m in yt.search(termo, filter="songs", limit=5):
        if m.get("videoId"):
            return {"id": m["videoId"], "titulo": m["title"],
                    "artista": ", ".join(a["name"] for a in m.get("artists") or [])}
    return None


NAVEGADORES = {"Opera", "Chrome", "Edge", "Firefox", "Brave"}


def pela_extensao(site, comando):
    """Pede pra extensão do navegador (via Claudinho) fazer isso na aba que já está aberta.
    Devolve True se tinha aba aberta e a extensão vai fazer; False se não (aí abre aba nova)."""
    import json
    import urllib.request
    try:
        chave = (sistema.DADOS / "ext_token").read_text(encoding="utf-8").strip()
        pedido = urllib.request.Request(
            "http://127.0.0.1:47821/ext/enviar", data=json.dumps({"site": site, "comando": comando}).encode(),
            headers={"Content-Type": "application/json", "X-Claudinho-Ext": chave})
        return bool(json.loads(urllib.request.urlopen(pedido, timeout=2).read()).get("entregue"))
    except Exception:
        return False


def abrir_aba_nova(url, focar=True):
    """Aba nova no navegador padrão. `focar=False`: devolve o foco pra janela que você estava usando."""
    try:
        import abrir
        if focar:
            abrir.abrir_site(url)  # abre e traz o navegador pra frente
            return
        import ctypes
        antes = ctypes.windll.user32.GetForegroundWindow()
        os.startfile(url)
        time.sleep(1.5)  # o navegador costuma pular pra frente ao abrir aba: devolve o foco
        abrir.forcar_frente(antes)
    except Exception:
        webbrowser.open(url)


def tocar_no_youtube_music(termo, artista=False):
    """Acha e toca no YouTube Music num rádio a partir da música: na aba que já está aberta (com a
    extensão do Claudinho) ou numa aba nova. Devolve a música ou None."""
    m = buscar(termo, artista)
    if not m:
        return None
    m["na_aba"] = tocar_url(f"https://music.youtube.com/watch?v={m['id']}&list=RDAMVM{m['id']}")
    return m


def tocar_id(video_id):
    """Toca no YouTube Music a música desse id (o que veio da lista da banda), num rádio a partir dela.
    list=RDAMVM<id>: rádio do YouTube Music começando por essa música (vai emendando parecidas)."""
    return tocar_url(f"https://music.youtube.com/watch?v={video_id}&list=RDAMVM{video_id}")


def tocar_url(url):
    """Abre um endereço do YouTube Music: na aba aberta (com a extensão) ou numa aba nova em segundo plano.
    Devolve True se foi na aba que já estava aberta."""
    atual = tocando()
    na_aba = pela_extensao("ytmusic", {"acao": "abrir", "url": url})
    # pausa o que estiver tocando, pra não sair duas músicas juntas (se for a própria aba, ela já troca)
    if atual and atual["tocando"] and not (na_aba and atual["app"] in NAVEGADORES):
        controlar("pausar")
        time.sleep(0.3)
    if not na_aba:
        abrir_aba_nova(url, focar=False)  # música toca em segundo plano: não rouba o foco
    return na_aba


def musicas_da_banda(nome, n=8):
    """As músicas mais ouvidas e os álbuns de uma banda/artista no YouTube Music.
    Devolve {'artista', 'musicas': [{'id', 'titulo', 'album'}], 'albuns': [{'titulo', 'ano'}]} ou None."""
    from ytmusicapi import YTMusic
    yt = YTMusic()
    achados = yt.search(nome, filter="artists", limit=1)
    if not achados:
        return None
    dados = yt.get_artist(achados[0]["browseId"])
    secao = dados.get("songs") or {}
    faixas = secao.get("results") or []
    if secao.get("browseId"):  # a página do artista só traz 5; a playlist "músicas" dele tem as outras
        try:
            faixas = yt.get_playlist(secao["browseId"], limit=n).get("tracks") or faixas
        except Exception:
            pass
    musicas = [{"id": m["videoId"], "titulo": m["title"], "album": (m.get("album") or {}).get("name", "")}
               for m in faixas if m.get("videoId")][:n]
    albuns = [{"titulo": a["title"], "ano": a.get("year", "")} for a in (dados.get("albums") or {}).get("results") or []][:6]
    return {"artista": dados.get("name") or achados[0].get("artist", nome), "musicas": musicas, "albuns": albuns}


def videos(termo, n=5):
    """Os primeiros vídeos da pesquisa do YouTube (lê a página de resultados; não precisa de chave de API).
    Devolve [{'id', 'titulo', 'canal', 'duracao', 'views'}]."""
    import json
    import re
    import urllib.request
    from urllib.parse import quote_plus
    pedido = urllib.request.Request(
        f"https://www.youtube.com/results?search_query={quote_plus(termo)}&hl=pt-BR&gl=BR",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
                 "Accept-Language": "pt-BR,pt;q=0.9"})
    html = urllib.request.urlopen(pedido, timeout=10).read().decode("utf-8")
    achado = re.search(r"var ytInitialData = (\{.*?\});</script>", html, re.S)
    if not achado:
        return []
    lista = []

    def andar(o):  # os vídeos ficam em "videoRenderer" no meio de um JSON enorme
        if len(lista) >= n:
            return
        if isinstance(o, dict):
            if "videoRenderer" in o:
                v = o["videoRenderer"]
                texto = lambda chave: (v.get(chave) or {}).get("simpleText", "")
                lista.append({"id": v["videoId"], "titulo": v["title"]["runs"][0]["text"],
                              "canal": ((v.get("ownerText") or {}).get("runs") or [{}])[0].get("text", ""),
                              "duracao": texto("lengthText"), "views": texto("viewCountText")})
            for x in o.values():
                andar(x)
        elif isinstance(o, list):
            for x in o:
                andar(x)

    andar(json.loads(achado.group(1)))
    return lista


def assistir(video_id):
    """Abre o vídeo do YouTube numa aba nova, na frente (pela extensão ou direto)."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    atual = tocando()
    if atual and atual["tocando"]:
        controlar("pausar")  # pra o vídeo não brigar com a música
    if not pela_extensao("youtube", {"acao": "abrir", "url": url, "nova": True, "focar": True}):
        abrir_aba_nova(url)


ACOES_PLAYER = ("pausar", "tocar", "proxima", "anterior", "aleatorio", "repetir", "volume")
ACOES_VIDEO = ("pausar", "tocar", "velocidade", "avancar", "voltar", "legenda", "cinema")


def no_player(site, acao, valor=None):
    """Mexe no player da aba aberta (YouTube Music ou YouTube) pela extensão. True se tinha aba pra isso."""
    return pela_extensao(site, {"acao": "controle", "qual": acao, "valor": valor})


def tocar_no_youtube(termo):
    """Pesquisa no YouTube e abre o primeiro vídeo, sempre numa aba nova e na frente (vídeo é pra ver).
    Devolve True se foi pela extensão (que também abre o primeiro resultado sozinha)."""
    from urllib.parse import quote_plus
    # #claudinho-tocar: a extensão abre o primeiro resultado sozinha (sem ela, fica a lista da pesquisa)
    url = f"https://www.youtube.com/results?search_query={quote_plus(termo)}#claudinho-tocar"
    atual = tocando()
    if atual and atual["tocando"]:
        controlar("pausar")
    if pela_extensao("youtube", {"acao": "abrir", "url": url, "nova": True, "focar": True}):
        return True
    abrir_aba_nova(url)
    return False


def descrever(m):
    if not m:
        return "nada tocando agora"
    musica = f"{m['titulo']} - {m['artista']}" if m["artista"] else m["titulo"]
    return f"{musica} (no {m['app']}, {'tocando' if m['tocando'] else 'pausado'})"


def main():
    acao = sys.argv[1] if len(sys.argv) > 1 else "tocando"
    if acao == "tocando":
        print(descrever(tocando()))
    elif acao in ("pausar", "tocar", "alternar", "proxima", "anterior"):
        if not controlar(acao):
            sys.exit("não consegui: nenhum player aberto ou ele não aceita esse comando")
        print(f"feito: {acao}")
    elif acao in ("buscar", "artista"):
        termo = " ".join(sys.argv[2:]).strip().strip('"')
        if not termo:
            sys.exit(f'uso: python musica.py {acao} "<termo>"')
        m = tocar_no_youtube_music(termo, artista=acao == "artista")
        if not m:
            sys.exit(f"não achei nada no YouTube Music pra: {termo}")
        onde = "na aba que já estava aberta" if m["na_aba"] else "numa aba nova"
        print(f"tocando no YouTube Music ({onde}): {m['titulo']} - {m['artista']} (depois segue num rádio parecido)")
    elif acao == "youtube":
        termo = " ".join(sys.argv[2:]).strip().strip('"')
        if not termo:
            sys.exit('uso: python musica.py youtube "<o que procurar>"')
        na_aba = tocar_no_youtube(termo)
        print(f"abri no YouTube, numa aba nova, o primeiro vídeo de: {termo}")
    elif acao == "curtir":
        if not pela_extensao("ytmusic", {"acao": "curtir"}):
            sys.exit("não consegui: precisa do YouTube Music aberto e da extensão do Claudinho no navegador")
        print("curti a música no YouTube Music")
    elif acao == "banda":
        nome = " ".join(sys.argv[2:]).strip().strip('"')
        b = musicas_da_banda(nome) if nome else None
        if not b or not b["musicas"]:
            sys.exit(f"não achei a banda no YouTube Music: {nome}")
        print(f"{b['artista']} — músicas mais ouvidas (id entre colchetes, pra tocar use tocar_id):")
        for i, m in enumerate(b["musicas"], 1):
            print(f"{i}. {m['titulo']}" + (f" ({m['album']})" if m["album"] else "") + f" [{m['id']}]")
        if b["albuns"]:
            print("Álbuns: " + "; ".join(f"{a['titulo']} ({a['ano']})" if a["ano"] else a["titulo"] for a in b["albuns"]))
    elif acao == "tocar_id":
        if len(sys.argv) < 3:
            sys.exit("uso: python musica.py tocar_id <id>")
        na_aba = tocar_id(sys.argv[2].strip())
        print(f"tocando no YouTube Music ({'na aba que já estava aberta' if na_aba else 'numa aba nova'}), "
              "depois segue num rádio parecido")
    elif acao == "curtidas":
        na_aba = tocar_url("https://music.youtube.com/watch?list=LM")  # LM = a playlist "Músicas que curti"
        print(f"tocando as suas curtidas no YouTube Music ({'na aba aberta' if na_aba else 'numa aba nova'})")
    elif acao in ("player", "video"):
        qual = sys.argv[2] if len(sys.argv) > 2 else ""
        valor = sys.argv[3] if len(sys.argv) > 3 else None
        permitidas = ACOES_PLAYER if acao == "player" else ACOES_VIDEO
        if qual not in permitidas:
            sys.exit(f"recusado: use uma destas: {', '.join(permitidas)}")
        site = "ytmusic" if acao == "player" else "youtube"
        if not no_player(site, qual, valor):
            sys.exit(f"não consegui: precisa do {'YouTube Music' if site == 'ytmusic' else 'YouTube'} aberto "
                     "e da extensão do Claudinho no navegador")
        print(f"feito: {qual}" + (f" {valor}" if valor else ""))
    elif acao == "videos":
        termo = " ".join(sys.argv[2:]).strip().strip('"')
        lista = videos(termo) if termo else []
        if not lista:
            sys.exit(f"não achei vídeos pra: {termo}")
        print(f"Vídeos no YouTube pra \"{termo}\" (id entre colchetes, pra abrir use assistir):")
        for i, v in enumerate(lista, 1):
            print(f"{i}. {v['titulo']} — {v['canal']}, {v['duracao']}, {v['views']} [{v['id']}]")
    elif acao == "assistir":
        if len(sys.argv) < 3:
            sys.exit("uso: python musica.py assistir <id>")
        assistir(sys.argv[2].strip())
        print("abri o vídeo no YouTube, numa aba nova")
    else:
        sys.exit(f"recusado: ação '{acao}' não existe (tocando, pausar, tocar, alternar, proxima, anterior, buscar, "
                 "artista, youtube, curtir, banda, tocar_id, curtidas, player, videos, assistir, video)")


if __name__ == "__main__":
    main()
