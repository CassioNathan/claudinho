"""O laço da tarefa autônoma, com um Claude e uma IA local de mentira."""
import threading

import autonomo


def montar(respostas, decisoes=(), sid_pai="pai-1"):
    """`respostas`: o que o subchat diz a cada rodada (texto, ou (texto, negados)). `decisoes`: o que a IA local
    responde quando ele para sem PRONTO."""
    chamadas, avisos = [], []
    fila, ideias = list(respostas), list(decisoes)

    def rodar_claude(cmd, cwd, entrada):
        chamadas.append((cmd, cwd, entrada))
        texto, negados = fila.pop(0) if isinstance(fila[0], tuple) else (fila.pop(0), [])
        return {"session_id": "filho-1", "result": texto, "total_cost_usd": 0.01, "permission_denials": negados}

    t = autonomo.Tarefa("implementa a tela de login", "1. criar a tela\n2. testes", "D:/proj", "proj",
                        sid_pai=sid_pai, rodar_claude=rodar_claude, decidir=lambda prompt: ideias.pop(0),
                        avisar=lambda tipo, tarefa, **extra: avisos.append((tipo, extra)))
    t.git = lambda *a: ""
    return t, chamadas, avisos


def test_primeira_rodada_copia_a_conversa_num_worktree_e_depois_continua():
    t, chamadas, avisos = montar(["Criei a tela.\nSTATUS: PERGUNTA", "Feito, testes ok.\nSTATUS: PRONTO"],
                                 ["RESPONDER: pode seguir o plano"])
    t.rodar()
    primeiro, segundo = chamadas[0][0], chamadas[1][0]
    assert "--fork-session" in primeiro and primeiro[primeiro.index("--resume") + 1] == "pai-1"
    assert primeiro[primeiro.index("-w") + 1] == t.nome and chamadas[0][1].endswith("proj")
    assert "PLANO:" in chamadas[0][2] and "1. criar a tela" in chamadas[0][2]
    assert segundo[segundo.index("--resume") + 1] == "filho-1" and "--fork-session" not in segundo
    assert chamadas[1][1] == str(t.worktree) and chamadas[1][2] == "pode seguir o plano"
    assert "Bash(git push:*)" in primeiro[primeiro.index("--disallowedTools") + 1]
    assert t.estado == "pronta" and t.resumo == "Feito, testes ok." and avisos[-1][0] == "pronta"


def test_sem_conversa_pra_copiar_comeca_um_chat_novo_no_worktree():
    t, chamadas, _ = montar(["ok\nSTATUS: PRONTO"], sid_pai=None)
    t.rodar()
    assert "--resume" not in chamadas[0][0] and "-w" in chamadas[0][0]


def test_duvida_vai_pro_seu_balao_e_sua_resposta_volta_pro_subchat():
    t, chamadas, avisos = montar(["Uso Postgres ou SQLite?\nSTATUS: PERGUNTA", "Feito.\nSTATUS: PRONTO"],
                                 ["USUARIO: escolha de banco"])

    def avisar(tipo, tarefa, **extra):
        avisos.append((tipo, extra))
        if tipo == "pergunta":
            assert "banco" in extra["motivo"]
            extra["pedido"]["texto"] = "SQLite"
            extra["pedido"]["evento"].set()
    t.avisar = avisar
    t.rodar()
    assert chamadas[1][2] == "SQLite" and t.estado == "pronta"


def test_comando_bloqueado_pede_pra_voce_e_liberar_tira_a_trava():
    negado = [{"tool_name": "Bash", "tool_input": {"command": "npm install"}}]
    t, chamadas, _ = montar([("Preciso instalar as dependências.\nSTATUS: TRAVADO", negado), "Feito.\nSTATUS: PRONTO"])

    def avisar(tipo, tarefa, **extra):
        if tipo == "pergunta":
            assert extra["negados"] == [{"comando": "npm install"}]
            extra["pedido"].update(texto="Liberei, pode rodar.", liberar=True)
            extra["pedido"]["evento"].set()
    t.avisar = avisar
    t.rodar()
    segundo = chamadas[1][0]
    assert "Bash(npm install)" in segundo[segundo.index("--allowedTools") + 1]
    assert "npm install" not in segundo[segundo.index("--disallowedTools") + 1]


def test_sem_resposta_sua_a_tarefa_para(monkeypatch):
    monkeypatch.setattr(autonomo, "ESPERA_VOCE_S", 0)
    t, _, avisos = montar(["Hmm?\nSTATUS: TRAVADO"])
    t.rodar()
    assert t.estado == "parada" and avisos[-1][0] == "parada"


def test_teto_de_rodadas(monkeypatch):
    monkeypatch.setattr(autonomo, "MAX_RODADAS", 2)
    monkeypatch.setattr(autonomo, "ESPERA_VOCE_S", 0)
    t, chamadas, avisos = montar(["a\nSTATUS: PERGUNTA", "b\nSTATUS: PERGUNTA"], ["RESPONDER: segue"])
    t.rodar()
    assert len(chamadas) == 2 and t.estado == "parada"
    assert any(tipo == "pergunta" and "rodadas" in extra["motivo"] for tipo, extra in avisos)


def test_erro_do_claude_vira_aviso_e_nao_derruba():
    t, _, avisos = montar([])
    t.rodar_claude = lambda *a: {"is_error": True, "result": "sem crédito"}
    t.rodar()
    assert t.estado == "falhou" and avisos[-1] == ("falhou", {"motivo": "sem crédito"})


def test_ler_decisao_na_duvida_chama_voce():
    assert autonomo.ler_decisao("RESPONDER: rode os testes") == ("responder", "rode os testes")
    assert autonomo.ler_decisao("**PRONTO**") == ("pronto", "")
    assert autonomo.ler_decisao("USUÁRIO: apagar pasta")[0] == "usuario"
    assert autonomo.ler_decisao("acho que sim")[0] == "usuario"
    assert autonomo.ler_decisao("RESPONDER:")[0] == "usuario"


def test_status_e_nome():
    assert autonomo.status_de("feito\nSTATUS: pronto") == "PRONTO"
    assert autonomo.status_de("sem status") is None
    assert autonomo.sem_status("Feito.\nSTATUS: PRONTO") == "Feito."
    assert autonomo.nome_curto("Implementa a tela de Login!").startswith("implementa-tela-login-")


def test_parar_no_meio():
    t, _, avisos = montar(["a\nSTATUS: PERGUNTA"], ["RESPONDER: segue"])
    t.parar = threading.Event()
    t.parar.set()
    t.rodar()
    assert t.estado == "parada"


def test_pronto_vale_mesmo_com_algo_bloqueado_no_caminho():
    negado = [{"tool_name": "Bash", "tool_input": {"command": "python -c 'import pytest'"}}]
    t, chamadas, avisos = montar([("Feito, testes ok.\nSTATUS: PRONTO", negado)])
    t.rodar()
    assert len(chamadas) == 1 and t.estado == "pronta"
