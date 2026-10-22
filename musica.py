"""O que está tocando no PC e controle do player, pelos controles de mídia do Windows
(os mesmos do controle de volume): vale pra Spotify, YouTube no navegador, YouTube Music etc.

Também é um ajudante limitado do chat, que roda sem confirmação:
    python musica.py tocando      mostra o que está tocando
    python musica.py pausar       pausa
    python musica.py tocar        volta a tocar
    python musica.py alternar     pausa/toca
    python musica.py proxima      pula pra próxima
    python musica.py anterior     volta pra anterior
"""
import asyncio
import sys
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
    else:
        sys.exit(f"recusado: ação '{acao}' não existe (tocando, pausar, tocar, alternar, proxima, anterior)")


if __name__ == "__main__":
    main()
