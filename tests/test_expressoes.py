"""Expressões (Zzz, lalala, ♪…♪) ficam no balão mas não vão pra voz."""
import pytest

import fala


@pytest.mark.parametrize("texto, falado", [
    ("Zzz... hã? Acordei!", "hã? Acordei!"),
    ("Lalala, que música boa!", "que música boa!"),
    ("♪ lá-lá-lá ♪ tum-tss, adoro essa batida", "adoro essa batida"),
    ("Hmmm, deixa eu ver.", "deixa eu ver."),
    ("kkkkk essa foi boa", "essa foi boa"),
    ("Uôu! Que legal", "Que legal"),
    ("Zzzzz", ""),
    ("♪♪♪", ""),
])
def test_expressao_some_da_voz(texto, falado):
    assert fala.limpar_para_fala(texto) == falado


@pytest.mark.parametrize("texto", ["Papai mandou o arquivo, vovó também.", "Café, coco e cocô.",
                                   "Assessoria e possessão ok", "Ele leu 3 arquivos e passou nos testes.",
                                   "Isso é sério: o deploy quebrou."])
def test_palavra_de_verdade_fica(texto):
    assert fala.limpar_para_fala(texto) == texto
