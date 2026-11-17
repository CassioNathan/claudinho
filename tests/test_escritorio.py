"""ClaudCorp: cargos, nomes fixos, subagentes e a gaveta de relatórios."""
import types

import escritorio as e


def test_cargo_do_chat_sobe_com_o_tempo_de_casa():
    assert e.cargo_do_chat(10 * 60) == "júnior"
    assert e.cargo_do_chat(2 * 3600) == "pleno"
    assert e.cargo_do_chat(5 * 3600) == "sênior"


def test_agente_simples_e_estagiario_e_o_resto_freela():
    assert e.cargo_do_agente("Explore") == "estagiário"
    assert e.cargo_do_agente("general-purpose", "Pesquisar a API do Stripe") == "estagiário"
    assert e.cargo_do_agente("general-purpose", "Procurar onde fica o login") == "estagiário"
    assert e.cargo_do_agente("general-purpose", "Implementar o checkout") == "freela"
    assert e.cargo_do_agente("Plan", "Planejar a migração") == "freela"


def test_mesmo_chat_e_sempre_a_mesma_pessoa():
    assert e.nome_de("chat:abc") == e.nome_de("chat:abc")
    assert e.visual_de("chat:abc") == e.visual_de("chat:abc")
    assert len({e.nome_de(f"chat:{i}") for i in range(30)}) > 10   # e cada um tem o seu
    sp = e.sprite(e.visual_de("chat:abc"))
    assert sp["corpo"].startswith("#") and isinstance(sp["direita"], list)


def test_subagente_do_chamado_ao_relatorio(tmp_path):
    esc = e.Escritorio(tmp_path / "relatorios.json")
    esc.chamou_agente("s1", {"subagent_type": "Explore", "description": "Procurar o login"})
    a = esc.agente_comecou({"session_id": "s1", "agent_id": "ag1", "agent_type": "Explore", "projeto": "lc-pedir"},
                           agora=100)
    assert a["cargo"] == "estagiário" and a["descricao"] == "Procurar o login"
    estado = esc.estado([], agora=110)
    assert [f["cargo"] for f in estado["funcionarios"]] == ["estagiário"]
    r = esc.agente_terminou({"agent_id": "ag1", "resultado": "Fica em src/login.ts"}, agora=120)
    assert r["texto"] == "Fica em src/login.ts" and r["projeto"] == "lc-pedir" and r["nome"] == e.nome_de("agente:ag1")
    assert not esc.subagentes
    assert e.Escritorio(tmp_path / "relatorios.json").relatorios[0]["titulo"] == "Procurar o login"   # ficou guardado


def test_estado_com_chats_e_fazer_sozinho(tmp_path):
    esc = e.Escritorio(tmp_path / "r.json")
    sessoes = [{"sid": "s1", "projeto": "lc-pedir", "estado": "trabalhando", "fazendo": "editando a.py",
                "pedido": "corrige o login", "criada": 0},
               {"sid": "auto-x1", "projeto": "lc-pedir 🤖", "estado": "trabalhando", "fazendo": ""}]
    parte = types.SimpleNamespace(id="x1", projeto="lc-pedir", titulo="front", pedido="tela nova")
    estado = esc.estado(sessoes, [parte], agora=5 * 3600)
    chat, freela = estado["funcionarios"]
    assert chat["cargo"] == "sênior" and chat["sala"] == "mesa" and chat["tarefa"] == "corrige o login"
    assert freela["cargo"] == "freela" and freela["sala"] == "reuniao"
    assert estado["projetos"] == ["lc-pedir"] and set(estado["sprites"]) == {"chat:s1", "chat:auto-x1"}


def test_gaveta_guarda_os_mais_novos_primeiro(tmp_path):
    esc = e.Escritorio(tmp_path / "r.json")
    for i in range(e.MAX_RELATORIOS + 5):
        esc.guardar(f"chat:{i}", "júnior", "p", f"t{i}", "x", agora=i + 1)
    assert len(esc.relatorios) == e.MAX_RELATORIOS and esc.relatorios[0]["titulo"] == f"t{e.MAX_RELATORIOS + 4}"
