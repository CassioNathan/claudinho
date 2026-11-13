"""Abaixa o som dos outros programas enquanto o Claudinho fala (e devolve quando ele termina).

Mexe só no volume de cada programa no mixer do Windows (as sessões de áudio da saída padrão), nunca no volume geral
nem no do próprio Claudinho. Guarda o volume de antes em ~/.claudinho/volume_abaixado.json: se ele fechar no meio da
fala, quem abrir depois devolve. Na volta, programa cujo volume você mexeu enquanto ele falava fica como você deixou.

Só comtypes (Core Audio direto), sem pacote a mais. Toda chamada roda numa thread com COM próprio.
"""
import ctypes
import json
import os
import threading
from ctypes import HRESULT, POINTER, byref, c_float, c_int, c_void_p
from ctypes.wintypes import BOOL, DWORD, LPCWSTR, LPWSTR

import comtypes
from comtypes import CLSCTX_ALL, COMMETHOD, GUID, IUnknown

import sistema

ARQUIVO = sistema.DADOS / "volume_abaixado.json"
FATOR = 0.3          # os outros ficam em 30% do volume que estavam
TOLERANCIA = 0.02    # na volta: volume diferente do que eu deixei = você mexeu, não devolvo


class ISimpleAudioVolume(IUnknown):
    _iid_ = GUID("{87CE5498-68D6-44E5-9215-6DA47EF883D8}")
    _methods_ = [
        COMMETHOD([], HRESULT, "SetMasterVolume", (["in"], c_float), (["in"], POINTER(GUID))),
        COMMETHOD([], HRESULT, "GetMasterVolume", (["out"], POINTER(c_float))),
        COMMETHOD([], HRESULT, "SetMute", (["in"], BOOL), (["in"], POINTER(GUID))),
        COMMETHOD([], HRESULT, "GetMute", (["out"], POINTER(BOOL))),
    ]


class IAudioSessionControl(IUnknown):
    _iid_ = GUID("{F4B1A599-7266-4319-A8CA-E70ACB11E8CD}")
    _methods_ = [
        COMMETHOD([], HRESULT, "GetState", (["out"], POINTER(c_int))),
        COMMETHOD([], HRESULT, "GetDisplayName", (["out"], POINTER(LPWSTR))),
        COMMETHOD([], HRESULT, "SetDisplayName", (["in"], LPCWSTR), (["in"], POINTER(GUID))),
        COMMETHOD([], HRESULT, "GetIconPath", (["out"], POINTER(LPWSTR))),
        COMMETHOD([], HRESULT, "SetIconPath", (["in"], LPCWSTR), (["in"], POINTER(GUID))),
        COMMETHOD([], HRESULT, "GetGroupingParam", (["out"], POINTER(GUID))),
        COMMETHOD([], HRESULT, "SetGroupingParam", (["in"], POINTER(GUID)), (["in"], POINTER(GUID))),
        COMMETHOD([], HRESULT, "RegisterAudioSessionNotification", (["in"], c_void_p)),
        COMMETHOD([], HRESULT, "UnregisterAudioSessionNotification", (["in"], c_void_p)),
    ]


class IAudioSessionControl2(IAudioSessionControl):
    _iid_ = GUID("{BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D}")
    _methods_ = [
        COMMETHOD([], HRESULT, "GetSessionIdentifier", (["out"], POINTER(LPWSTR))),
        COMMETHOD([], HRESULT, "GetSessionInstanceIdentifier", (["out"], POINTER(LPWSTR))),
        COMMETHOD([], HRESULT, "GetProcessId", (["out"], POINTER(DWORD))),
        COMMETHOD([], HRESULT, "IsSystemSoundsSession"),
        COMMETHOD([], HRESULT, "SetDuckingPreference", (["in"], BOOL)),
    ]


class IAudioSessionEnumerator(IUnknown):
    _iid_ = GUID("{E2F5BB11-0570-40CA-ACDD-3AA01277DEE8}")
    _methods_ = [
        COMMETHOD([], HRESULT, "GetCount", (["out"], POINTER(c_int))),
        COMMETHOD([], HRESULT, "GetSession", (["in"], c_int), (["out"], POINTER(POINTER(IAudioSessionControl)))),
    ]


class IAudioSessionManager2(IUnknown):
    _iid_ = GUID("{77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F}")
    _methods_ = [
        COMMETHOD([], HRESULT, "GetAudioSessionControl", (["in"], POINTER(GUID)), (["in"], DWORD),
                  (["out"], POINTER(POINTER(IUnknown)))),
        COMMETHOD([], HRESULT, "GetSimpleAudioVolume", (["in"], POINTER(GUID)), (["in"], DWORD),
                  (["out"], POINTER(POINTER(ISimpleAudioVolume)))),
        COMMETHOD([], HRESULT, "GetSessionEnumerator", (["out"], POINTER(POINTER(IAudioSessionEnumerator)))),
        COMMETHOD([], HRESULT, "RegisterSessionNotification", (["in"], c_void_p)),
        COMMETHOD([], HRESULT, "UnregisterSessionNotification", (["in"], c_void_p)),
        COMMETHOD([], HRESULT, "RegisterDuckNotification", (["in"], LPCWSTR), (["in"], c_void_p)),
        COMMETHOD([], HRESULT, "UnregisterDuckNotification", (["in"], c_void_p)),
    ]


class IMMDevice(IUnknown):
    _iid_ = GUID("{D666063F-1587-4E43-81F1-B948E807363F}")
    _methods_ = [
        COMMETHOD([], HRESULT, "Activate", (["in"], POINTER(GUID)), (["in"], DWORD), (["in"], c_void_p),
                  (["out"], POINTER(POINTER(IUnknown)))),
    ]


class IMMDeviceEnumerator(IUnknown):
    _iid_ = GUID("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
    _methods_ = [
        COMMETHOD([], HRESULT, "EnumAudioEndpoints", (["in"], c_int), (["in"], DWORD), (["out"], POINTER(c_void_p))),
        COMMETHOD([], HRESULT, "GetDefaultAudioEndpoint", (["in"], c_int), (["in"], c_int),
                  (["out"], POINTER(POINTER(IMMDevice)))),
    ]


CLSID_ENUMERADOR = GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}")


def _sessoes():
    """[(pid, ISimpleAudioVolume)] da saída padrão (sem o som do sistema)."""
    enumerador = comtypes.CoCreateInstance(CLSID_ENUMERADOR, IMMDeviceEnumerator, CLSCTX_ALL)
    dispositivo = enumerador.GetDefaultAudioEndpoint(0, 1)   # eRender, eMultimedia
    gerente = dispositivo.Activate(byref(IAudioSessionManager2._iid_), CLSCTX_ALL, None)
    gerente = gerente.QueryInterface(IAudioSessionManager2)
    lista = gerente.GetSessionEnumerator()
    saida = []
    for i in range(lista.GetCount()):
        controle = lista.GetSession(i).QueryInterface(IAudioSessionControl2)
        pid = controle.GetProcessId()
        if pid:
            saida.append((pid, controle.QueryInterface(ISimpleAudioVolume)))
    return saida


def _com(funcao, *args):
    """Roda numa thread com COM próprio e espera (no máximo 3 s: áudio travado não trava o Claudinho)."""
    resultado = {}

    def rodar():
        comtypes.CoInitialize()
        try:
            resultado["v"] = funcao(*args)
        except Exception as e:
            resultado["erro"] = e
        finally:
            comtypes.CoUninitialize()
    t = threading.Thread(target=rodar, daemon=True)
    t.start()
    t.join(3)
    return resultado.get("v")


def _ler():
    try:
        return {int(k): v for k, v in json.loads(ARQUIVO.read_text(encoding="utf-8")).items()}
    except (OSError, ValueError, AttributeError):
        return {}


def _gravar(guardado):
    try:
        if guardado:
            ARQUIVO.write_text(json.dumps(guardado), encoding="utf-8")
        else:
            ARQUIVO.unlink(missing_ok=True)
    except OSError:
        pass


def _abaixar(fator, eu):
    guardado = _ler()
    for pid, vol in _sessoes():
        if pid == eu or pid in guardado:
            continue
        antes = vol.GetMasterVolume()
        if antes <= 0.01:
            continue
        depois = round(antes * fator, 3)
        vol.SetMasterVolume(depois, None)
        guardado[pid] = [antes, depois]
    _gravar(guardado)
    return len(guardado)


def _restaurar():
    guardado = _ler()
    for pid, vol in _sessoes():
        if pid in guardado:
            antes, depois = guardado[pid]
            if abs(vol.GetMasterVolume() - depois) <= TOLERANCIA:   # você não mexeu enquanto eu falava
                vol.SetMasterVolume(antes, None)
    _gravar({})


class Abaixador:
    """`falando(sim)` a cada volta do laço: abaixa quando começa, devolve um pouco depois de acabar."""
    DEVOLVER_DEPOIS_S = 0.8

    def __init__(self):
        self.abaixado = False
        self.calado_desde = None
        self.trava = threading.Lock()

    def falando(self, sim, ligado=True, agora=None):
        import time
        agora = time.time() if agora is None else agora
        if sim and ligado and not self.abaixado:
            self.abaixado = True
            self.calado_desde = None
            threading.Thread(target=self._fazer, args=(True,), daemon=True).start()
        elif self.abaixado and (not sim or not ligado):
            self.calado_desde = self.calado_desde or agora
            if agora - self.calado_desde >= self.DEVOLVER_DEPOIS_S or not ligado:
                self.abaixado = False
                self.calado_desde = None
                threading.Thread(target=self._fazer, args=(False,), daemon=True).start()
        elif sim:
            self.calado_desde = None

    def _fazer(self, abaixar):
        with self.trava:
            if abaixar:
                _com(_abaixar, FATOR, os.getpid())
            else:
                _com(_restaurar)


def restaurar_se_ficou():
    """Na abertura: o Claudinho fechou no meio de uma fala? Devolve o volume dos outros."""
    if ARQUIVO.exists():
        _com(_restaurar)


if __name__ == "__main__":   # teste na mão: lista os programas com som e o volume de cada um
    comtypes.CoInitialize()
    for p, v in _sessoes():
        print(p, round(v.GetMasterVolume(), 2))
    ctypes.windll.kernel32.Sleep(0)
