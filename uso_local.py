"""Quanto a IA local (Ollama) está pesando no PC agora: CPU e RAM dos processos dela, e a placa de vídeo.

Só mede quando alguém pergunta (o painel, a cada 3 s): a medição roda num fio à parte e a resposta é a última
leitura, então o painel nunca espera o nvidia-smi.
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import shutil
import subprocess
import threading
import time
import urllib.request

OLLAMA = "http://127.0.0.1:11434"
NOMES = {"ollama.exe", "ollama_llama_server.exe"}   # o servidor e o "runner" que carrega o modelo

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_psapi = ctypes.WinDLL("psapi", use_last_error=True)
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TH32CS_SNAPPROCESS = 0x2


class _ENTRADA(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                ("th32ParentProcessID", wt.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                ("szExeFile", ctypes.c_wchar * 260)]


class _MEMORIA(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t)]


_k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
_k32.OpenProcess.restype = wt.HANDLE


def _pids_do_ollama():
    snap = _k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == wt.HANDLE(-1).value:
        return []
    pids, e = [], _ENTRADA()
    e.dwSize = ctypes.sizeof(_ENTRADA)
    try:
        ok = _k32.Process32FirstW(snap, ctypes.byref(e))
        while ok:
            if e.szExeFile.lower() in NOMES:
                pids.append(e.th32ProcessID)
            ok = _k32.Process32NextW(snap, ctypes.byref(e))
    finally:
        _k32.CloseHandle(snap)
    return pids


def _tempo_e_memoria(pid):
    """(segundos de CPU usados até agora, bytes de RAM) de um processo, ou None."""
    h = _k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None
    try:
        c, s, k, u = wt.FILETIME(), wt.FILETIME(), wt.FILETIME(), wt.FILETIME()
        if not _k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(s), ctypes.byref(k), ctypes.byref(u)):
            return None
        cpu = sum((t.dwHighDateTime << 32 | t.dwLowDateTime) for t in (k, u)) / 1e7
        m = _MEMORIA()
        m.cb = ctypes.sizeof(_MEMORIA)
        ram = m.WorkingSetSize if _psapi.GetProcessMemoryInfo(h, ctypes.byref(m), m.cb) else 0
        return cpu, ram
    finally:
        _k32.CloseHandle(h)


def _gpu():
    """(uso da placa toda em %, VRAM usada da placa em MB, VRAM total em MB) ou None sem placa NVIDIA."""
    if not shutil.which("nvidia-smi"):
        return None
    try:
        saida = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
                                "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5,
                               creationflags=subprocess.CREATE_NO_WINDOW).stdout
        uso, usada, total = (int(x) for x in saida.splitlines()[0].split(","))
        return uso, usada, total
    except Exception:
        return None


def _modelos_carregados():
    """[(nome, MB na placa de vídeo)] do que o Ollama tem na memória agora."""
    try:
        with urllib.request.urlopen(OLLAMA + "/api/ps", timeout=2) as r:
            dados = json.load(r)
        return [(m.get("name", "?"), round(m.get("size_vram", 0) / 2**20)) for m in dados.get("models", [])]
    except Exception:
        return []


_ULTIMA = {"pedido": 0.0, "medindo": False, "valor": None, "antes": None}
_NUCLEOS = os.cpu_count() or 1


def _medir():
    try:
        agora = time.monotonic()
        pids = _pids_do_ollama()
        leituras = {p: v for p in pids if (v := _tempo_e_memoria(p))}
        anterior = _ULTIMA["antes"]
        cpu = None
        if anterior:
            t0, tempos0 = anterior
            gasto = sum(v[0] - tempos0[p] for p, v in leituras.items() if p in tempos0)
            cpu = max(0.0, min(100.0, 100 * gasto / max(agora - t0, 0.001) / _NUCLEOS))
        _ULTIMA["antes"] = (agora, {p: v[0] for p, v in leituras.items()})
        gpu = _gpu() if pids else None
        modelos = _modelos_carregados() if pids else []
        _ULTIMA["valor"] = {
            "rodando": bool(pids),
            "cpu": None if cpu is None else round(cpu, 1),
            "ram_mb": round(sum(v[1] for v in leituras.values()) / 2**20),
            "gpu": None if not gpu else {"uso": gpu[0], "usada_mb": gpu[1], "total_mb": gpu[2]},
            "modelos": [{"nome": n, "vram_mb": v} for n, v in modelos],
        }
    finally:
        _ULTIMA["medindo"] = False


def agora():
    """A última leitura (e pede outra em segundo plano). None até a primeira terminar."""
    if not _ULTIMA["medindo"] and time.time() - _ULTIMA["pedido"] > 2:
        _ULTIMA["pedido"], _ULTIMA["medindo"] = time.time(), True
        threading.Thread(target=_medir, daemon=True).start()
    return _ULTIMA["valor"]
