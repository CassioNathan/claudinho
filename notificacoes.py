"""Lê e limpa as notificações da central do Windows (WinRT UserNotificationListener).

Uso no terminal: python notificacoes.py  -> lista o que tem lá."""
import asyncio
from datetime import datetime

from winrt.windows.ui.notifications import KnownNotificationBindings, NotificationKinds
from winrt.windows.ui.notifications.management import UserNotificationListener, UserNotificationListenerAccessStatus


async def _ouvinte():
    ouvinte = UserNotificationListener.current
    if ouvinte.get_access_status() != UserNotificationListenerAccessStatus.ALLOWED:
        if await ouvinte.request_access_async() != UserNotificationListenerAccessStatus.ALLOWED:
            raise PermissionError("O Windows não liberou ler as notificações "
                                  "(Configurações > Privacidade > Notificações).")
    return ouvinte


async def _listar():
    ouvinte = await _ouvinte()
    achadas = []
    for n in await ouvinte.get_notifications_async(NotificationKinds.TOAST):
        try:
            app = n.app_info.display_info.display_name if n.app_info else "?"
        except Exception:
            app = "?"
        linhas = []
        try:
            visual = n.notification.visual.get_binding(KnownNotificationBindings.toast_generic)
            linhas = [t.text.strip() for t in visual.get_text_elements() if t.text and t.text.strip()] if visual else []
        except Exception:
            pass
        quando = datetime.fromtimestamp(n.creation_time.timestamp()) if n.creation_time else None
        achadas.append({"id": n.id, "app": app, "titulo": linhas[0] if linhas else "",
                        "texto": " ".join(linhas[1:]), "quando": quando})
    return sorted(achadas, key=lambda a: a["quando"] or datetime.min, reverse=True)


async def _limpar(ids):
    ouvinte = await _ouvinte()
    for i in ids:
        try:
            ouvinte.remove_notification(i)
        except Exception:
            pass


def listar():
    """Notificações da central, da mais nova pra mais velha: [{id, app, titulo, texto, quando}]."""
    return asyncio.run(_listar())


def limpar(ids):
    """Tira da central só estas notificações (as que chegaram depois ficam)."""
    asyncio.run(_limpar(list(ids)))


if __name__ == "__main__":
    for a in listar():
        print(f"{a['quando']:%d/%m %H:%M}  {a['app']}: {a['titulo']} — {a['texto'][:80]}")
