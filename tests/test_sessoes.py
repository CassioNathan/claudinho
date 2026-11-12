"""A lista viva das sessões do Claude Code e o Pode/Não pelo balão (hook PermissionRequest)."""
import io
import json
import sys
from pathlib import Path

import sessoes
import sistema

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hook"))
import claudinho_notificar  # noqa: E402


def aviso(evento, **extra):
    return dict({"evento": evento, "session_id": "s1", "projeto": "lc-pedir", "pasta": "D:/lc-pedir"}, **extra)


def test_sessao_vai_de_pedido_a_pronto(tmp_path):
    s = sessoes.Sessoes(tmp_path / "sessoes.json")
    s.registrar(aviso("inicio"), agora=100)
    s.registrar(aviso("pedido", pedido="corrige o login"), agora=110)
    s.registrar(aviso("ferramenta", ferramenta="Bash", entrada={"description": "Rodar os testes"}), agora=120)
    [atual] = s.ativas(agora=130)
    assert atual["estado"] == "trabalhando" and atual["fazendo"] == "rodar os testes"
    assert "lc-pedir: trabalhando" in s.descrever(agora=130) and "corrige o login" in s.descrever(agora=130)
    s.registrar({"session_id": "s1", "projeto": "lc-pedir", "resumo": "Corrigi o login."}, agora=140)  # Stop antigo
    assert s.ativas(agora=150)[0]["estado"] == "pronto"
    assert "terminei (Corrigi o login.)" in s.descrever(agora=150)
    # o MCP lê o que ficou gravado
    assert sessoes.Sessoes.ler(tmp_path / "sessoes.json").ativas(agora=150)[0]["projeto"] == "lc-pedir"


def test_esperando_vem_primeiro_e_fechada_sai(tmp_path):
    s = sessoes.Sessoes()
    s.registrar(aviso("pedido", pedido="a"), agora=100)
    s.registrar(dict(aviso("espera", mensagem="preciso de você"), session_id="s2", projeto="claudinho"), agora=105)
    assert [x["sid"] for x in s.ativas(agora=110)] == ["s2", "s1"]
    s.registrar(aviso("fechou"), agora=120)
    assert [x["sid"] for x in s.ativas(agora=121)] == ["s2"]


def test_trabalhando_sem_noticia_vira_parada_e_velha_some():
    s = sessoes.Sessoes()
    s.registrar(aviso("pedido", pedido="a"), agora=0)
    assert s.ativas(agora=sessoes.TRAVADA_S + 1)[0]["estado"] == "parada"
    assert s.ativas(agora=sessoes.VELHA_S + 1) == []


def test_o_que_faz_em_portugues():
    assert sessoes.o_que_faz("Edit", {"file_path": "C:/x/motores.py"}) == "editando motores.py"
    assert sessoes.o_que_faz("Bash", {}) == "rodando um comando"
    assert sessoes.o_que_faz("mcp__claudinho__ver_tela", {}) == "usando ver tela"


def rodar_hook(monkeypatch, capsys, dados, resposta):
    enviados = []

    def enviar(caminho, corpo, espera=1.5):
        enviados.append((caminho, corpo))
        return json.dumps(resposta).encode() if resposta is not None else None
    monkeypatch.setattr(claudinho_notificar, "enviar", enviar)
    monkeypatch.delenv("CLAUDINHO_CHAT", raising=False)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(json.dumps(dados).encode())))
    claudinho_notificar.main()
    return enviados, capsys.readouterr().out


PEDIDO = {"hook_event_name": "PermissionRequest", "session_id": "s1", "cwd": "D:/lc-pedir", "tool_name": "Bash",
          "tool_input": {"command": "npm test", "description": "rodar os testes"}}


def test_permissao_pelo_balao_pode(monkeypatch, capsys):
    enviados, saida = rodar_hook(monkeypatch, capsys, PEDIDO, {"decisao": "allow"})
    assert enviados[0][0] == "/permissao" and enviados[0][1]["entrada"]["command"] == "npm test"
    assert json.loads(saida)["hookSpecificOutput"]["decision"] == {"behavior": "allow"}


def test_permissao_pelo_balao_nao(monkeypatch, capsys):
    _, saida = rodar_hook(monkeypatch, capsys, PEDIDO, {"decisao": "deny"})
    assert json.loads(saida)["hookSpecificOutput"]["decision"]["behavior"] == "deny"


def test_permissao_sem_resposta_fica_no_app(monkeypatch, capsys):
    assert rodar_hook(monkeypatch, capsys, PEDIDO, {"decisao": ""})[1] == ""
    assert rodar_hook(monkeypatch, capsys, PEDIDO, None)[1] == ""   # Claudinho fechado


def test_pergunta_com_opcoes_nao_vem_pro_balao(monkeypatch, capsys):
    enviados, saida = rodar_hook(monkeypatch, capsys, dict(PEDIDO, tool_name="AskUserQuestion"), {"decisao": "allow"})
    assert enviados == [] and saida == ""


def test_ferramenta_manda_so_o_leve(monkeypatch, capsys):
    dados = {"hook_event_name": "PreToolUse", "session_id": "s1", "cwd": "D:/x", "tool_name": "Write",
             "tool_input": {"file_path": "D:/x/a.py", "content": "segredo" * 100}}
    enviados, _ = rodar_hook(monkeypatch, capsys, dados, None)
    assert enviados[0][1]["entrada"] == {"file_path": "D:/x/a.py"}


def test_ligar_aviso_poe_os_eventos_novos(tmp_path, monkeypatch):
    monkeypatch.setattr(sistema, "CLAUDE", tmp_path)
    sistema.ligar_aviso(True)
    dados = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
    pre = dados["hooks"]["PreToolUse"][0]["hooks"][0]
    perm = dados["hooks"]["PermissionRequest"][0]["hooks"][0]
    assert pre["async"] is True and "async" not in perm and perm["timeout"] > claudinho_notificar.ESPERA_PERMISSAO_S
    # já atualizado: o atualizar_aviso não mexe de novo
    antes = (tmp_path / "settings.json").read_text(encoding="utf-8")
    sistema.atualizar_aviso()
    assert (tmp_path / "settings.json").read_text(encoding="utf-8") == antes
