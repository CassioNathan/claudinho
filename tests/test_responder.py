"""A regra do tempo de responder um chat pelo balão (30 s pra começar, depois tempo pra escrever devagar)."""
import responder


def pedido(criado=0.0, **kw):
    p = responder.novo({"session_id": "s1", "projeto": "lc-pedir"})
    p.update(criado=criado, **kw)
    return p


def test_prazo_muda_conforme_voce_age():
    p = pedido()
    assert responder.prazo(p) == responder.APARECER_S            # balão ainda nem apareceu
    p["mostrado"] = 10
    assert responder.prazo(p) == 10 + responder.COMECAR_S        # apareceu: 30 s pra começar
    p["comecou"] = 35
    assert responder.prazo(p) == 35 + responder.ESCREVER_S       # começou: dá pra digitar devagar
    p["comecou"] = 700
    assert responder.prazo(p) == responder.TOTAL_S               # mas nunca passa do total


def test_esperar_desiste_quando_o_prazo_passa():
    p = pedido(mostrado=1)
    tempos = iter([5, 20, responder.COMECAR_S + 2])
    responder.esperar(p, relogio=lambda: next(tempos), passo=0)
    assert p["evento"].is_set() and p["texto"] is None


def test_entregar_e_desistir():
    p = pedido()
    responder.entregar(p, "roda os testes")
    responder.desistir(p)                                       # depois de entregue, não apaga
    assert p["texto"] == "roda os testes" and not responder.pendente(p)
    q = pedido()
    responder.desistir(q)
    responder.entregar(q, "tarde demais")
    assert q["texto"] is None
