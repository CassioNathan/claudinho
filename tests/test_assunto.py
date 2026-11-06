"""Linha de raciocínio: um assunto por vez (assunto.py) e a ordem de `enviar` no claudinho.pyw."""
import re
from collections import deque
from pathlib import Path

from assunto import ASSUNTO_S, Assunto

RAIZ = Path(__file__).resolve().parent.parent


def test_sem_assunto_no_comeco():
    assert not Assunto().ativo(agora=1000)


def test_marcar_abre_e_expira_depois_do_silencio():
    a = Assunto()
    a.marcar(agora=1000)
    assert a.ativo(agora=1000 + ASSUNTO_S - 1)
    assert not a.ativo(agora=1000 + ASSUNTO_S + 1)


def test_cada_mensagem_renova_os_4_minutos():
    a = Assunto()
    a.marcar(agora=1000)
    a.marcar(agora=1000 + ASSUNTO_S - 10)
    assert a.ativo(agora=1000 + ASSUNTO_S + 100)
    assert ASSUNTO_S == 240


def test_comentario_no_meio_do_assunto_nao_entra():
    a = Assunto()
    a.marcar(agora=1000)
    assert a.ativo(agora=1100)            # quem puxa assunto sozinho checa isto e espera


def test_pensando_ou_conversa_aberta_conta_como_assunto():
    a = Assunto()
    assert a.ativo(ocupado=True, agora=5000)
    assert a.ativo(entrada=True, agora=5000)


def test_marcar_tira_piada_da_fila_e_mantem_o_resto():
    falas = deque([{"texto": "piada", "piada": True}, {"texto": "aviso"}])
    Assunto().marcar(falas, agora=1000)
    assert [f["texto"] for f in falas] == ["aviso"]


def test_enviar_vazio_nao_renova_o_silencio():
    """Em `enviar`, a checagem de texto vazio vem antes de marcar_assunto()."""
    fonte = (RAIZ / "claudinho.pyw").read_text(encoding="utf-8")
    corpo = fonte.split("    def enviar(self, e=None", 1)[1].split("\n    def ", 1)[0]
    vazio = re.search(r"if not texto:\s*\n\s*return", corpo)
    assert vazio and vazio.start() < corpo.index("self.marcar_assunto()")
