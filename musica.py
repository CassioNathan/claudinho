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

Buscar e tocar usa o YouTube Music sem login (ytmusicapi) só pra achar a música; quem toca é o seu
navegador, logado na sua conta. Antes de abrir, pausa o que estiver tocando pra não sair duas músicas.
"""
import asyncio
import sys
import time
import webbrowser
from pathlib import Path

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


def tocar_no_youtube_music(termo, artista=False):
    """Acha e abre no YouTube Music, já tocando, num rádio a partir da música. Devolve a música ou None."""
    m = buscar(termo, artista)
    if not m:
        return None
    atual = tocando()
    if atual and atual["tocando"]:
        controlar("pausar")  # pra não ficar a música velha e a nova juntas
        time.sleep(0.3)
    # list=RDAMVM<id>: rádio do YouTube Music começando por essa música (vai emendando parecidas)
    url = f"https://music.youtube.com/watch?v={m['id']}&list=RDAMVM{m['id']}"
    try:
        import abrir  # abre no navegador padrão e traz a janela pra frente
        abrir.abrir_site(url)
    except Exception:
        webbrowser.open(url)
    return m


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
        print(f"tocando no YouTube Music: {m['titulo']} - {m['artista']} (depois segue num rádio parecido)")
    else:
        sys.exit(f"recusado: ação '{acao}' não existe "
                 "(tocando, pausar, tocar, alternar, proxima, anterior, buscar, artista)")


if __name__ == "__main__":
    main()
