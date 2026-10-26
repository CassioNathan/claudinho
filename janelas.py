"""Lê as janelas abertas no Windows (título, programa, posição) sem tirar print."""
import ctypes
import ctypes.wintypes as wt
import time
from pathlib import Path

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
dwmapi = ctypes.windll.dwmapi

kernel32.OpenProcess.restype = wt.HANDLE
user32.GetForegroundWindow.restype = wt.HWND
ENUM = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
WS_EX_TOOLWINDOW = 0x80
IGNORAR = {"python.exe", "pythonw.exe", "textinputhost.exe", "applicationframehost.exe",
           "shellexperiencehost.exe", "searchhost.exe", "startmenuexperiencehost.exe",
           "claudinho.exe", "claudinho-cli.exe"}  # o próprio Claudinho empacotado


def exe_de(hwnd):
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(520)
        n = wt.DWORD(520)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
            return Path(buf.value).name.lower()
        return ""
    finally:
        kernel32.CloseHandle(h)


def oculta(hwnd):
    cloaked = ctypes.c_int(0)
    dwmapi.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
    return bool(cloaked.value)


def janela_ativa():
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    return descrever(hwnd)


def descrever(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return {"hwnd": hwnd, "titulo": buf.value, "exe": exe_de(hwnd),
            "rect": (r.left, r.top, r.right, r.bottom)}


def _cpu_segundos(pid):
    """Tempo de CPU que o processo já usou (kernel + usuário), em segundos; None se não der pra ler."""
    h = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return None
    try:
        criado, saiu, kernel, usuario = (wt.FILETIME() for _ in range(4))
        if not kernel32.GetProcessTimes(h, ctypes.byref(criado), ctypes.byref(saiu), ctypes.byref(kernel),
                                        ctypes.byref(usuario)):
            return None
        junta = lambda f: (f.dwHighDateTime << 32 | f.dwLowDateTime) / 1e7  # noqa: E731
        return junta(kernel) + junta(usuario)
    finally:
        kernel32.CloseHandle(h)


def esperar_pronta(achar, limite=120.0, calma=0.6, por=2.0):
    """Espera a janela que `achar()` devolve aparecer e o programa sossegar: CPU abaixo de `calma` núcleo por `por`
    segundos seguidos (IntelliJ abrindo projeto fica em vários núcleos; pronto, quase zero). -> (janela, segundos, pronta)
    pronta=False quando estourou o limite (achou a janela mas ainda trabalhando, ou nem achou)."""
    inicio = time.time()
    janela, ultimo, calmo_desde = None, None, None
    while time.time() - inicio < limite:
        janela = achar() if not janela else janela
        if janela and user32.IsWindow(janela["hwnd"]):
            pid = wt.DWORD()
            user32.GetWindowThreadProcessId(janela["hwnd"], ctypes.byref(pid))
            agora, cpu = time.time(), _cpu_segundos(pid.value)
            if cpu is not None and ultimo:
                uso = (cpu - ultimo[1]) / max(0.05, agora - ultimo[0])
                calmo_desde = (calmo_desde or agora) if uso < calma else None
                if calmo_desde and agora - calmo_desde >= por:
                    return descrever(janela["hwnd"]), round(agora - inicio, 1), True
            ultimo = (agora, cpu) if cpu is not None else None
        else:
            janela = None
        time.sleep(0.5)
    return (descrever(janela["hwnd"]) if janela else None), round(time.time() - inicio, 1), False


def no_ponto(lista, x, y):
    """A janela mais à frente que contém o ponto (a lista já vem da frente para trás)."""
    for j in lista:
        esq, topo, dir_, base = j["rect"]
        if esq <= x < dir_ and topo <= y < base:
            return j
    return None


def listar(area=None):
    """Janelas visíveis de verdade, da frente para trás. `area` filtra pelo monitor."""
    achadas = []

    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        if not user32.GetWindowTextLengthW(hwnd) or oculta(hwnd):
            return True
        if user32.GetWindowLongW(hwnd, -20) & WS_EX_TOOLWINDOW:
            return True
        j = descrever(hwnd)
        esq, topo, dir_, base = j["rect"]
        if dir_ - esq < 200 or base - topo < 150 or j["exe"] in IGNORAR:
            return True
        if area:
            cx, cy = (esq + dir_) / 2, (topo + base) / 2
            if not (area[0] <= cx < area[2] and area[1] <= cy < area[3]):
                return True
        achadas.append(j)
        return True

    user32.EnumWindows(ENUM(cb), 0)
    return achadas
