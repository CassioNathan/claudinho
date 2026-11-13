"""Quando o som dos outros abaixa e volta (sem mexer no áudio de verdade)."""
import abaixar


def montar(monkeypatch):
    feito = []
    a = abaixar.Abaixador()
    monkeypatch.setattr(a, "_fazer", lambda abaixando: feito.append(abaixando))
    monkeypatch.setattr(abaixar.threading, "Thread",
                        lambda target, args, daemon: type("T", (), {"start": lambda s: target(*args)})())
    return a, feito


def test_abaixa_ao_falar_e_volta_depois_de_um_tempinho(monkeypatch):
    a, feito = montar(monkeypatch)
    a.falando(True, agora=0)
    a.falando(True, agora=1)
    assert feito == [True]
    a.falando(False, agora=2)            # calou: ainda não devolve (pode vir a próxima frase)
    a.falando(True, agora=2.3)           # veio: continua abaixado, sem abaixar de novo
    a.falando(False, agora=3)
    assert feito == [True]
    a.falando(False, agora=3 + abaixar.Abaixador.DEVOLVER_DEPOIS_S + 0.01)
    assert feito == [True, False] and not a.abaixado


def test_desligado_nao_abaixa_e_desligar_no_meio_devolve(monkeypatch):
    a, feito = montar(monkeypatch)
    a.falando(True, ligado=False, agora=0)
    assert feito == []
    a.falando(True, agora=1)
    a.falando(True, ligado=False, agora=1.1)
    assert feito == [True, False]
