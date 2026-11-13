"""Trocar o visual pelo chat ("pirata roxo", "aleatório", "padrão")."""
import random

import pytest

import ajustes_chat as aj
import skins


@pytest.mark.parametrize("qual, valor, esperado", [
    ("júnior", "liga", ("modo_junior", True)),
    ("resumo", "desligar", ("resumir_avisos", False)),
    ("ultron", "ligar", ("personalidade", "ultron")),
    ("ultron", "desliga", ("personalidade", "claudinho")),
    ("movimento", "de lado", ("movimento", "horizontal")),
    ("volume", "150", ("voz_volume", 100)),
    ("voz_silencio", "1,5", ("voz_silencio", 1.5)),
    ("frequencia", "de vez em quando", ("comentar_a_cada_minutos", [15, 30])),
    ("comentar_a_cada_minutos", "5 a 2", ("comentar_a_cada_minutos", [2, 5])),
    ("voz_apelidos", "Ei Claudinho, Fala aí", ("voz_apelidos", ["Ei Claudinho", "Fala aí"])),
])
def test_interpretar(qual, valor, esperado):
    assert aj.interpretar(qual, valor, {}) == esperado


@pytest.mark.parametrize("qual, valor, cfg", [
    ("motor", "api", {}),                         # segurança: só no painel
    ("pastas_leitura", "C:/", {}),
    ("vendado", "desligar", {"vendado": True}),   # faixa só sai pelo painel
    ("microfone", "ligar", {"voz": False}),       # microfone só liga pelo painel
    ("ver_tela", "ligar", {"ver_tela": False}),
    ("modo_junior", "talvez", {}),
])
def test_recusa(qual, valor, cfg):
    with pytest.raises(ValueError):
        aj.interpretar(qual, valor, cfg)


def test_opcoes_de_fora():
    extra = {"chat_esforco": {"low": "low", "high": "high"}}
    assert aj.interpretar("esforço", "high", {}, extra) == ("chat_esforco", "high")
    assert "ligado" in aj.listar({"modo_junior": True})


def test_pacote_e_cor_juntos():
    novo, texto = skins.escolher_visual("vira pirata roxo", skins.VISUAL_PADRAO)
    assert novo["cor"] == "roxo" and novo["olhos"] == "tapa_olho" and "Pirata" in texto


def test_adereco_mantem_o_resto():
    atual = dict(skins.VISUAL_PADRAO, cor="azul")
    novo, _ = skins.escolher_visual("bota uma coroa", atual)
    assert novo["cabeca"] == "coroa" and novo["cor"] == "azul"


def test_aleatorio_sempre_valido():
    r = random.Random(7)
    for _ in range(30):
        novo, _ = skins.escolher_visual("aleatório", skins.VISUAL_PADRAO, r)
        assert novo == skins.visual_valido(novo)


def test_padrao_e_desconhecido():
    assert skins.escolher_visual("volta pro padrão", {"cor": "roxo"})[0] == skins.VISUAL_PADRAO
    novo, texto = skins.escolher_visual("banana", skins.VISUAL_PADRAO)
    assert novo is None and "Pacotes" in texto
