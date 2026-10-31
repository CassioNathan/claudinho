"""Testes das partes que não abrem janela: o que a banca de revisão achou quebrado fica coberto aqui."""
import io
import json
import time

import pytest

import atualizacao
import consumo
import revisao
import sistema


# ---------- versão nova ----------
@pytest.mark.parametrize("texto, esperado", [("v1.10.2", (1, 10, 2)), ("", ()), (None, ()), ("1.3.0-beta", (1, 3, 0))])
def test_numero_da_versao(texto, esperado):
    assert atualizacao.numero(texto) == esperado


def test_versao_compara_como_numero():
    assert atualizacao.numero("1.10") > atualizacao.numero("1.9")


class _Resposta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.mark.parametrize("corpo", [b"[]", b"null", b'"texto"', b"<html>"])
def test_versao_nova_com_resposta_estranha(monkeypatch, corpo):
    monkeypatch.setattr(atualizacao.urllib.request, "urlopen", lambda *a, **k: _Resposta(corpo))
    assert atualizacao.nova() is None


def test_versao_nova_com_link_de_fora(monkeypatch):
    corpo = json.dumps({"tag_name": "v99.0.0", "html_url": "https://evil.tld/x"}).encode()
    monkeypatch.setattr(atualizacao.urllib.request, "urlopen", lambda *a, **k: _Resposta(corpo))
    assert atualizacao.nova()["url"].startswith("https://github.com/CassioNathan/claudinho/")


def test_versao_nova_sem_rede(monkeypatch):
    def cair(*a, **k):
        raise OSError("sem rede")
    monkeypatch.setattr(atualizacao.urllib.request, "urlopen", cair)
    assert atualizacao.nova() is None


# ---------- consumo ----------
@pytest.mark.parametrize("conteudo", ["[]", "null", "42", '"texto"', '{"total": {"desde": "2026-01-01"}}', "{quebrado"])
def test_consumo_aguenta_arquivo_estranho(conteudo):
    consumo.ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    consumo.ARQUIVO.write_text(conteudo, encoding="utf-8")
    consumo.registrar("chat", 0.01, 10, 5)
    dados = consumo.do_claudinho()
    assert dados["hoje"]["chamadas"] == 1 and dados["total"]["entrada"] == 10


def test_consumo_soma():
    consumo.ARQUIVO.unlink(missing_ok=True)
    consumo.registrar("piadas", "0.02", "50", 10)
    consumo.registrar("piadas", 0.03, 0, 0)
    c = consumo.do_claudinho()
    assert c["hoje"]["chamadas"] == 2 and c["hoje"]["por_tarefa"]["piadas"] == pytest.approx(0.05)


def test_custo_api_com_dict_e_id_com_data():
    uso = {"input_tokens": 1_000_000, "output_tokens": 0}
    assert consumo.custo_api("claude-haiku-5-5-20261001", uso) == pytest.approx(0.10)


def test_preco_vem_da_tabela_de_modelos():
    import motores
    for m in motores.MODELOS.values():
        assert consumo.preco(m["id"]) == m["preco"]
    assert consumo.preco("modelo-novo") == motores.MODELOS["sonnet"]["preco"]
    assert set(motores.MODELOS_CLAUDE) == set(motores.MODELOS)


def test_janelas_do_plano_zera_as_resetadas():
    plano = {"rate_limits": {"five_hour": {"used_percentage": "40", "resets_at": time.time() + 3600},
                             "seven_day": {"used_percentage": 90, "resets_at": 1}}}
    janelas = consumo.janelas_do_plano(plano)
    assert janelas["five_hour"]["pct"] == 40 and not janelas["five_hour"]["resetou"]
    assert janelas["seven_day"] == {"pct": 0, "reseta": None, "resetou": True}
    assert consumo.janelas_do_plano({"rate_limits": "lixo"}) == {} and consumo.janelas_do_plano({}) == {}


def test_texto_do_consumo_sem_recebido():
    consumo.PLANO.write_text(json.dumps({"rate_limits": {"five_hour": {"used_percentage": "40"}}}), encoding="utf-8")
    assert "não sei quando" in consumo.texto()


# ---------- revisor do Júnior ----------
def test_extrair_json_com_texto_depois():
    texto = '{"feito": true, "resumo": "ok"}\nObs.: o dict {a: 1} no teste está certo.'
    assert revisao.extrair_json(texto) == {"feito": True, "resumo": "ok"}


@pytest.mark.parametrize("texto", ["", "sem json", "{quebrado", None])
def test_extrair_json_sem_json(texto):
    assert revisao.extrair_json(texto) is None


@pytest.mark.parametrize("comando", ["npm test & calc", "powershell -enc xyz", "npm test | cmd", "rm -rf /", "python x.py"])
def test_teste_fora_da_lista_nao_roda(tmp_path, comando):
    assert revisao.comando_de_teste(comando, tmp_path) is None


def test_teste_nao_usa_programa_de_dentro_do_projeto(tmp_path, monkeypatch):
    falso = tmp_path / "npm"
    falso.write_text("")
    monkeypatch.setattr(revisao.shutil, "which", lambda *a, **k: str(falso))
    assert revisao.comando_de_teste("npm test", tmp_path) is None


def test_wrapper_do_projeto_so_se_existir(tmp_path):
    assert revisao.comando_de_teste("mvnw test", tmp_path) is None
    (tmp_path / "mvnw.cmd").write_text("")
    assert revisao.comando_de_teste("./mvnw test", tmp_path)[0].endswith("mvnw.cmd")


def test_rodar_teste_passou_e_falhou(tmp_path):
    import sys
    assert revisao.rodar_teste([sys.executable, "-c", "print('ok')"], tmp_path)[0] == "passou"
    assert revisao.rodar_teste([sys.executable, "-c", "import sys; sys.exit(3)"], tmp_path)[:2] == ("falhou", 3)


def test_rodar_teste_demorou(tmp_path):
    import sys
    situacao, codigo, _ = revisao.rodar_teste([sys.executable, "-c", "import time; time.sleep(30)"], tmp_path, limite=1)
    assert (situacao, codigo) == ("demorou", None)


# ---------- hooks ----------
def test_barra_de_status_com_numero_em_texto():
    import claudinho_status
    assert claudinho_status.janela("5h", {"used_percentage": "40", "resets_at": str(time.time() + 3600)}).startswith("5h 40%")
    assert claudinho_status.janela("5h", "lixo") is None


def test_aviso_com_input_estranho(tmp_path):
    import claudinho_notificar
    linhas = [{"type": "user", "message": {"content": "arruma o botão"}},
              {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Edit", "input": "x"},
                                                            {"type": "text", "text": "pronto"}]}}]
    arq = tmp_path / "t.jsonl"
    arq.write_text("\n".join(json.dumps(x) for x in linhas), encoding="utf-8")
    pedido, resposta, mexeu = claudinho_notificar.ultimos(str(arq))
    assert (pedido, resposta, mexeu) == ("arruma o botão", "pronto", [])


# ---------- sistema ----------
def test_barra_ligada_reconhece_o_comando(monkeypatch):
    monkeypatch.setattr(sistema, "_ler_settings", lambda: {"statusLine": {"command": sistema.comando_texto("status")}})
    assert sistema.barra_ligada()
    monkeypatch.setattr(sistema, "_ler_settings", lambda: {"statusLine": {"command": "minha-barra.sh"}})
    assert not sistema.barra_ligada()


# ---------- treino da voz ----------
def test_nota_do_checkpoint():
    import pipeline
    assert pipeline.nota("epoch=120-val_mel=0.3914.ckpt", "val_mel") == pytest.approx(0.3914)
    assert pipeline.nota("epoch=1-val_mel=5e-05.ckpt", "val_mel") == pytest.approx(5e-05)
    assert pipeline.nota("last.ckpt", "val_mel") is None


def _treino_falso(tmp_path, monkeypatch, com_ckpt, epoca_feita=100):
    import pipeline
    pasta = tmp_path / "voz"
    (pasta / "treino").mkdir(parents=True)
    (pasta / "metadata.csv").write_text("\n".join(f"a{i}|frase" for i in range(pipeline.MIN_FRASES_TREINO)), encoding="utf-8")
    (pasta / "config.json").write_text("{}")
    if com_ckpt:
        (pasta / "treino" / "last.ckpt").write_bytes(b"")
    chamadas = []
    monkeypatch.setattr(pipeline, "epoca_do_checkpoint", lambda c: epoca_feita)
    monkeypatch.setattr(pipeline.subprocess, "run", lambda cmd, **kw: chamadas.append(cmd) or type("R", (), {"returncode": 0})())

    class T:
        voz = "teste"
        def progresso(self, **kw): pass
    T.pasta = pasta
    return pipeline, T(), chamadas


def test_continuar_sem_checkpoint(tmp_path, monkeypatch):
    pipeline, t, chamadas = _treino_falso(tmp_path, monkeypatch, com_ckpt=False)
    with pytest.raises(SystemExit):
        pipeline.treinar(t, 500, continuar=True)
    assert not chamadas


def test_continuar_com_limite_menor_que_a_epoca(tmp_path, monkeypatch):
    pipeline, t, chamadas = _treino_falso(tmp_path, monkeypatch, com_ckpt=True, epoca_feita=149)
    with pytest.raises(SystemExit):
        pipeline.treinar(t, 149, continuar=True)
    assert not chamadas


def test_continuar_normal(tmp_path, monkeypatch):
    pipeline, t, chamadas = _treino_falso(tmp_path, monkeypatch, com_ckpt=True, epoca_feita=149)
    pipeline.treinar(t, 500, continuar=True)
    assert "--ckpt_path" in chamadas[0] and "500" in chamadas[0]


def test_normalizar_frase():
    import pipeline
    assert pipeline.normalizar("Ação, João!  Ñ") == "acao joao n"


# ---------- vigia: chat do Claude Code esperando você ----------
@pytest.mark.parametrize("dados, sim", [({"notification_type": "permission_prompt"}, True),
                                        ({"notification_type": "elicitation_dialog"}, True),
                                        ({"notification_type": "idle_prompt"}, False),
                                        ({"message": "Claude needs your permission to use Bash"}, True),
                                        ({"message": "Claude is waiting for your input"}, False)])
def test_hook_so_avisa_quando_espera_voce(dados, sim):
    import claudinho_notificar
    assert claudinho_notificar.esperando_voce(dados) == sim


def test_ligar_aviso_poe_stop_e_notification(tmp_path, monkeypatch):
    monkeypatch.setattr(sistema, "CLAUDE", tmp_path)
    (tmp_path / "settings.json").write_text(json.dumps({"hooks": {"Stop": [{"hooks": [
        {"type": "command", "command": "meu-hook.sh"}]}]}}), encoding="utf-8")
    sistema.ligar_aviso(True)
    dados = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
    assert sistema.aviso_ligado() and sistema._nossos(dados, "Notification") == [sistema.comando_texto("aviso")]
    assert dados["hooks"]["Stop"][0]["hooks"][0]["command"] == "meu-hook.sh"   # o hook da pessoa fica
    sistema.ligar_aviso(False)
    dados = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
    assert "Notification" not in dados["hooks"] and not sistema.aviso_ligado()
    assert dados["hooks"]["Stop"][0]["hooks"][0]["command"] == "meu-hook.sh"


# ---------- comandos rápidos da voz ----------
@pytest.mark.parametrize("frase, esperado", [
    ("Pausa.", ("pausar", None)), ("Claudinho, pula essa música", ("proxima", None)), ("continua", ("tocar", None)),
    ("toca Legião Urbana", ("musica", "legiao urbana")), ("coloca Coldplay pra tocar", ("musica", "coldplay")),
    ("abre o Spotify", ("abrir", "spotify")), ("que horas são?", ("horas", None)),
    ("põe um timer de cinco minutos", ("timer", (300, ""))),
    ("me lembra em 20 minutos de tirar o bolo", ("timer", (1200, "tirar o bolo"))),
    ("aumenta o volume", ("volume_mais", None)), ("muta", ("mudo", None))])
def test_comando_rapido(frase, esperado):
    import comandos
    assert comandos.entender(frase) == esperado


@pytest.mark.parametrize("frase", ["abre o projeto e me diz o que tem", "toca no YouTube o vídeo do gato",
                                   "me explica o que é um hook", "para de falar", "timer de muito tempo",
                                   "qual é a capital da França e quantos habitantes ela tem hoje em dia"])
def test_conversa_vai_pro_chat(frase):
    import comandos
    assert comandos.entender(frase) is None


def test_dica_de_vocabulario_curta():
    import voz
    v = voz.Voz.__new__(voz.Voz)
    v.vocabulario = lambda: "Spotify, , IntelliJ, Spotify, " + ", ".join(f"projeto{i}" for i in range(100))
    dica = v._dica_vocabulario()
    assert dica.startswith("Spotify, IntelliJ, projeto0") and len(dica) <= voz.MAX_DICA + 1
    v.vocabulario = lambda: ""
    assert v._dica_vocabulario() is None


# ---------- palavra de ativação ----------
def test_ativacao_sem_modelo_usa_o_whisper(tmp_path, monkeypatch):
    import ativacao
    monkeypatch.setattr(ativacao, "PASTA", tmp_path)
    monkeypatch.setattr(ativacao, "MODELO", tmp_path / "claudinho.onnx")
    monkeypatch.setattr(ativacao, "INFO", tmp_path / "claudinho.json")
    assert not ativacao.disponivel()
    assert ativacao.limiar() == ativacao.LIMIAR_PADRAO
    (tmp_path / "claudinho.json").write_text('{"limiar": 0.37}', encoding="utf-8")
    assert ativacao.limiar() == pytest.approx(0.37)
    (tmp_path / "claudinho.json").write_text("[1, 2]", encoding="utf-8")
    assert ativacao.limiar() == ativacao.LIMIAR_PADRAO


def test_voz_sem_detector_fica_no_jeito_antigo(monkeypatch):
    import ativacao
    import voz
    monkeypatch.setattr(ativacao, "disponivel", lambda: False)
    v = voz.Voz.__new__(voz.Voz)
    v.config, v.detector, v.detector_versao, v.detector_erro = (lambda: {"voz_detector": True}), None, None, None
    v._atualizar_detector()
    assert v.detector is None


# ---------- comandos de vídeo, tela e abas ----------
@pytest.mark.parametrize("frase, esperado", [
    ("Tá beleza, rola um pouco mais.", ("rolar_baixo", None)), ("rola pra cima", ("rolar_cima", None)),
    ("Na verdade, pausa o vídeo que tá tocando.", ("video_pausar", None)), ("dá play", ("video_tocar", None)),
    ("avança 30 segundos", ("video_avancar", 30)), ("volta dez segundos", ("video_voltar", 10)),
    ("volta pro YouTube", ("ir_aba", "youtube")), ("fecha a aba da Strandberg", ("fechar_aba", "strandberg")),
    ("fecha essa aba", ("fechar_aba", "")), ("sobe o volume", ("volume_mais", None))])
def test_comandos_de_video_e_abas(frase, esperado):
    import comandos
    assert comandos.entender(frase) == esperado


def test_achar_aba_pelo_nome():
    import abas
    lista = [{"id": 1, "titulo": "Strandberg Boden Essential 6 - YouTube", "site": "www.youtube.com", "ativa": True},
             {"id": 2, "titulo": "Caixa de entrada - Gmail", "site": "mail.google.com"},
             {"id": 3, "titulo": "AliExpress Black Friday - YouTube", "site": "www.youtube.com", "tocando": True}]
    assert abas.achar("estrangberg", lista)["id"] == 1
    assert abas.achar("gmail", lista)["id"] == 2
    assert abas.achar("youtube", lista)["id"] == 3   # a que está tocando
    assert abas.achar("netflix", lista) is None


# ---------- meus comandos e roteador ----------
def test_meus_comandos():
    import meus_comandos as m
    lista = m.validar_lista([{"nome": "Modo trabalho", "frases": ["modo trabalho", "bora trabalhar"],
                              "acoes": [{"tipo": "programa", "valor": "IntelliJ"}, {"tipo": "rm", "valor": "x"}]},
                             {"nome": "vazio", "acoes": []}, "lixo"])
    assert len(lista) == 1 and [a["tipo"] for a in lista[0]["acoes"]] == ["programa"]
    assert m.achar("Ei, bora trabalha", lista)["nome"] == "Modo trabalho"
    assert m.achar("que horas são", lista) is None
    assert not m.vale_rotear("como funciona o hook?") and m.vale_rotear("deixa o vídeo parado")
    assert m.ler_roteador('{"id": "video_pausar"}', lista) == ("video_pausar", None)
    assert m.ler_roteador('{"id": "meu:Modo trabalho"}', lista)[0] == "meu"
    assert m.ler_roteador('{"id": "apagar_tudo"}', lista) is None
    assert m.ler_roteador('{"id": "ir_aba", "arg": ""}', lista) is None


def test_nome_aproximado_com_detector_seguro():
    import voz
    assert voz.nome_aproximado("Acrojinho.", "Claudinho") == (True, "")
    assert voz.nome_aproximado("E Claudim, toca algo", "Claudinho") == (True, "toca algo")
    assert not voz.nome_aproximado("Tem nada de ver o que está acontecendo.", "Claudinho")[0]


def test_fluxo_aprendido():
    import meus_comandos as m
    passos = [{"nome": "mcp__claudinho__abas_navegador", "entrada": {}},                       # só olhou: fica de fora
              {"nome": "mcp__claudinho__abrir_programa", "entrada": {"nome": "intelij"}, "ok": False},   # falhou
              {"nome": "mcp__claudinho__abrir_programa", "entrada": {"nome": "IntelliJ"}},
              {"nome": "mcp__claudinho__esperar_janela", "entrada": {"janela": "intellij"}},
              {"nome": "mcp__claudinho__atalho", "entrada": {"teclas": "shift+f10", "janela": "intellij"}}]
    acoes = m.fluxo_de_passos(passos)
    assert [a["tipo"] for a in acoes] == ["programa", "esperar", "atalho"] and acoes[0]["valor"] == "IntelliJ"
    assert m.fluxo_de_passos([{"nome": "Bash", "entrada": {"command": 'python abrir.py pesquisa "lo fi" youtube'}}])[0][
        "valor"] == "https://www.youtube.com/results?search_query=lo+fi"
    # passo que não dá pra repetir sem a IA (comando qualquer, tecla confirmada, arquivo): não aprende
    assert m.fluxo_de_passos(passos + [{"nome": "Bash", "entrada": {"command": "dir"}}]) is None
    assert m.fluxo_de_passos([{"nome": "mcp__claudinho__atalho_confirmado", "entrada": {"teclas": "enter"}}]) is None
    assert m.fluxo_de_passos([{"nome": "mcp__claudinho__ver_tela", "entrada": {}}]) is None   # nada feito
    assert m.vale_aprender("Ei Claudinho, abre o IntelliJ e roda") and not m.vale_aprender("como funciona o hook?")
    lista, motivo = m.aprender([], "Ei Claudinho, roda o projeto.", acoes)
    assert motivo is None and lista[0]["nome"] == "Roda o projeto" and lista[0]["acoes"][-1]["tipo"] == "falar"
    assert m.achar("roda o projeto", lista)["nome"] == "Roda o projeto"
    lista, _ = m.aprender(lista, "roda o projeto", acoes[:1])   # a mesma frase troca o que tinha
    assert len(lista) == 1 and len(lista[0]["acoes"]) == 2


def test_fluxo_sem_ruido():
    import meus_comandos as m
    tela = {"nome": "mcp__claudinho__ver_tela", "entrada": {}}
    tecla = lambda t, v=1: {"nome": "mcp__claudinho__atalho", "entrada": {"teclas": t, "vezes": v}}  # noqa: E731
    # o caso de ontem: Ctrl+número várias vezes, olhando a tela, até achar o YouTube
    procura = m.fluxo_de_passos([tela, tecla("ctrl+2"), tela, tecla("ctrl+5"), tela, tecla("ctrl+tab", 3), tela])
    assert procura and m.limpar_fluxo(procura) == ([], True)
    assert m.enxugar("vai pro youtube", procura) is None                     # sem a revisão: não grava pela metade
    revisor = lambda prompt: '{"manter": [0, 1], "aba": "youtube"}'           # noqa: E731  (0 e 1 são procura)
    assert m.enxugar("vai pro youtube", procura, revisor) == [{"tipo": "aba", "valor": "youtube", "janela": ""}]
    assert m.enxugar("vai pro youtube", procura, lambda p: "não sei") is None
    # o revisor não inventa: número que não existe some, e sem aba nem passo bom não sobra nada
    assert m.ler_enxugar('{"manter": [99, "x"], "aba": ""}', procura) is None
    # repetição boba e abas seguidas: só as regras locais resolvem (sem chamar ninguém)
    sujo = m.fluxo_de_passos([{"nome": "mcp__claudinho__abrir_programa", "entrada": {"nome": "Spotify"}},
                              {"nome": "mcp__claudinho__abrir_programa", "entrada": {"nome": "Spotify"}},
                              {"nome": "mcp__claudinho__ir_para_aba", "entrada": {"nome": "gmail"}},
                              {"nome": "mcp__claudinho__ir_para_aba", "entrada": {"nome": "youtube"}},
                              tecla("down", 3)])
    chamou = []
    limpo = m.enxugar("x", sujo, lambda p: chamou.append(p))
    assert not chamou and [(a["tipo"], a["valor"]) for a in limpo] == [
        ("programa", "Spotify"), ("aba", "youtube"), ("atalho", "down"), ("atalho", "down"), ("atalho", "down")]
    assert m.descrever(limpo[:2]) == "abrir Spotify → ir pra aba youtube"


def test_hibrido_local():
    import motores
    import meus_comandos as m
    # "local" só vale onde o modelo pequeno dá conta; na revisão volta pro padrão
    v = motores.modelos_validos({"roteador": "local", "revisao": "local", "piadas": "sonnet"})
    assert v["roteador"] == "local" and v["revisao"] == "sonnet" and v["piadas"] == "sonnet"
    motores.configurar("claude_code", "qwen3:1.7b", {"avisos": "local"})
    try:
        assert motores.na_nuvem("avisos") == "haiku" and motores.usa_local()
        assert not motores.local_pode([{"type": "image"}])   # print com modelo que não enxerga: vai pra nuvem
    finally:
        motores.configurar("claude_code", "qwen3:1.7b", None)
    assert motores.usa_local()   # o híbrido é o padrão (sem Ollama, vai pro Haiku sozinho)
    motores.configurar("claude_code", "qwen3:1.7b", {"avisos": "haiku", "roteador": "haiku"})
    assert not motores.usa_local()
    motores.configurar("claude_code", "qwen3:1.7b", None)
    lista = [{"nome": "Modo trabalho", "frases": ["modo trabalho"], "acoes": []}]
    assert m.ler_roteador('{"id": "meu", "arg": "modo trabalho"}', lista)[0] == "meu"


# ---------- modo híbrido: tarefas na hora marcada ----------
def test_modo_ia():
    import motores
    try:
        motores.configurar("claude_code", "qwen3:1.7b", None)
        assert motores.modo_ia() == "hibrido"   # o padrão
        motores.configurar("claude_code", "qwen3:1.7b", {"avisos": "haiku", "roteador": "haiku"})
        assert motores.modo_ia() == "nuvem"
        motores.configurar("ollama", "qwen3:1.7b", None)
        assert motores.modo_ia() == "local"
    finally:
        motores.configurar("claude_code", "qwen3:1.7b", None)


@pytest.mark.parametrize("frase, pedido, hora, repetir", [
    ("Claudinho, às 18h abre o Spotify e toca lo-fi", "abre o Spotify e toca lo-fi", "18:00", None),
    ("abre o IntelliJ às 18:30", "abre o IntelliJ", "18:30", None),
    ("todo dia às 8h toca lo-fi", "toca lo-fi", "08:00", "diaria"),
    ("dias úteis às 9 abre o Teams pra mim", "abre o Teams", "09:00", "uteis"),
    ("às 7 da noite fecha o jogo", "fecha o jogo", "19:00", None),
    ("me lembra amanhã às 9 de pagar a conta", "pagar a conta", "09:00", "uma"),
    ("ei claudinho me avisa ao meio dia de almoçar", "almoçar", "12:00", None),
])
def test_tarefa_entendida(frase, pedido, hora, repetir):
    import tarefas
    e = tarefas.entender(frase)
    assert e and (e["pedido"], e["hora"], e["repetir"]) == (pedido, hora, repetir)


@pytest.mark.parametrize("frase", ["o que eu fiz às 18h ontem?", "abre as 3 abas", "toca as 10", "abre o spotify"])
def test_nao_e_tarefa(frase):
    import tarefas
    assert tarefas.entender(frase) is None


def test_tarefa_proxima_e_perdida():
    import datetime as dt
    import tarefas
    sexta_17h = dt.datetime(2026, 10, 30, 17, 0).timestamp()   # 30/10/2026 é sexta
    t, erro = tarefas.nova("abre o teams", "09:00", "uteis", agora=sexta_17h)
    assert not erro and dt.datetime.fromtimestamp(t["proxima"]) == dt.datetime(2026, 11, 2, 9, 0)   # pula o fim de semana
    s, _ = tarefas.nova("toca rock", "17:30", "semanal", agora=sexta_17h)
    assert s["dia"] == 4 and dt.datetime.fromtimestamp(s["proxima"]) == dt.datetime(2026, 10, 30, 17, 30)
    u, _ = tarefas.nova("x y", "08:00", "uma", agora=sexta_17h)
    assert u["data"] == "2026-10-31"   # 8h já passou hoje: amanhã
    # venceu às 17:30; o Claudinho abriu 18:20 (PC desligado na hora): perdida. Aberto desde antes: faz
    assert tarefas.vencidas([s], s["proxima"] + 50 * 60, aberto_em=s["proxima"] + 49 * 60)[0][1] == "perdida"
    assert tarefas.vencidas([s], s["proxima"] + 50 * 60, aberto_em=sexta_17h)[0][1] == "fazer"
    assert tarefas.vencidas([s], s["proxima"] + 10 * 60, aberto_em=s["proxima"] + 5 * 60)[0][1] == "fazer"
    tarefas.avancar(u, u["proxima"] + 1)
    assert not u["ativa"] and u["proxima"] is None   # uma vez: rodou, parou
    tarefas.avancar(s, s["proxima"] + 1)
    assert dt.datetime.fromtimestamp(s["proxima"]) == dt.datetime(2026, 11, 6, 17, 30)


def test_tarefas_do_painel():
    import tarefas
    lista = tarefas.validar_lista([{"pedido": "abre o spotify", "hora": "18:00", "repetir": "diaria"},
                                   {"pedido": "", "hora": "18:00"}, {"pedido": "x", "hora": "25:00"}, "lixo"])
    assert len(lista) == 1 and lista[0]["id"] and lista[0]["proxima"]
    assert tarefas.repeticao_da_resposta("uma vez por semana") == "semanal"
    assert tarefas.repeticao_da_resposta("só hoje") == "uma"
    assert tarefas.repeticao_da_resposta("dias úteis") == "uteis"


# ---------- ficha dos programas ----------
def test_ficha_basica_sem_ia():
    import fichas
    jogo = fichas.basica("eldenring.exe", r"D:\SteamLibrary\steamapps\common\ELDEN RING\Game\eldenring.exe",
                         {"produto": "ELDEN RING"})
    assert (jogo["nome"], jogo["categoria"], jogo["comentar"]) == ("ELDEN RING", "jogo", "pouco")
    assert fichas.basica("code.exe")["categoria"] == "programacao"
    assert fichas.basica("opera.exe", site="youtube.com", titulo="Algum vídeo - YouTube")["categoria"] == "video"
    assert fichas.basica("opera.exe", site="exemplo.com.br")["categoria"] == "outro"   # site não é "o navegador"


def test_ficha_chave_do_navegador_e_do_site():
    import fichas
    assert fichas.chave("chrome.exe", "www.YouTube.com") == "site:youtube.com"
    assert fichas.chave("chrome.exe") == "exe:chrome.exe"
    assert fichas.chave("cs2.exe", "youtube.com") == "exe:cs2.exe"   # site só vale no navegador


def test_ficha_no_prompt_e_onde_comentar():
    import fichas
    jogo = {"nome": "CS2", "categoria": "jogo", "o_que_e": "jogo de tiro", "faz": "", "comentar": "pouco"}
    assert "nunca descreva a interface" in fichas.contexto(jogo)
    assert fichas.contexto(None) == ""
    assert fichas.pode_comentar(None) and not fichas.pode_comentar(dict(jogo, comentar="nao"))


def test_ficha_corrigida_por_voce_nao_e_refeita(monkeypatch, tmp_path):
    import fichas
    monkeypatch.setattr(fichas, "ARQUIVO", tmp_path / "fichas.json")
    fichas.gravar({"site:lc.com.br": dict(fichas.basica("opera.exe", site="lc.com.br"), quando=0)})
    assert fichas.corrigir("site:lc.com.br", {"faz": "atendendo chamados", "comentar": "nao", "categoria": "xyz"})
    f = fichas.buscar("opera.exe", "lc.com.br")
    assert (f["faz"], f["comentar"], f["categoria"], f["origem"]) == ("atendendo chamados", "nao", "outro", "voce")
    chamou = []
    monkeypatch.setattr(fichas.threading, "Thread", lambda *a, **k: chamou.append(1))
    fichas.garantir({"exe": "opera.exe", "hwnd": 0, "titulo": ""}, "lc.com.br")
    assert not chamou
    assert fichas.apagar("site:lc.com.br") and fichas.buscar("opera.exe", "lc.com.br") is None


def test_ficha_generica_e_dominio():
    import fichas
    assert fichas.generica({"categoria": "outro", "o_que_e": "sistema de vendas"})
    assert fichas.generica({"categoria": "trabalho", "o_que_e": "um site que permite navegar na internet"})
    assert not fichas.generica({"categoria": "video", "o_que_e": "site de vídeos online"})
    assert fichas.dominio_raiz("portal.lcsistemas.com.br") == "lcsistemas.com.br"
    assert fichas.dominio_raiz("music.youtube.com") == "youtube.com"


def test_ficha_le_a_pagina_do_site(monkeypatch):
    import fichas
    pagina = ('<html><head><title>LC Sistemas | Revendas</title><meta content="ERP Web e PIX" name="description">'
              "<meta property='og:site_name' content='LC Sistemas'></head></html>")
    monkeypatch.setattr(fichas, "_baixar", lambda url, **k: pagina)
    assert fichas.pesquisar_site("lcsistemas.com.br") == {"nome": "LC Sistemas", "texto": "LC Sistemas | Revendas; ERP Web e PIX"}

    def sem_rede(url, **k):
        raise OSError
    monkeypatch.setattr(fichas, "_baixar", sem_rede)
    assert fichas.pesquisar_site("x.com.br") == {}


def test_ficha_pesquisa_uma_vez_so(monkeypatch, tmp_path):
    import fichas
    monkeypatch.setattr(fichas, "ARQUIVO", tmp_path / "fichas.json")
    pesquisas = []
    monkeypatch.setattr(fichas, "pesquisar_site", lambda s: pesquisas.append(s) or {"nome": "LC Sistemas", "texto": "ERP Web e PIX"})
    monkeypatch.setattr(fichas, "completar_com_local", lambda *a, **k: None)   # local ocupado (treino, jogo…)
    janela = {"exe": "opera.exe", "hwnd": 0, "titulo": ""}
    fichas._gerar("site:lcsistemas.com.br", janela, "lcsistemas.com.br", "", None)
    f = fichas.buscar("opera.exe", "lcsistemas.com.br")
    assert (f["nome"], f["o_que_e"], f["origem"]) == ("LC Sistemas", "ERP Web e PIX", "basica")   # a descrição achada já serve
    fichas._gerar("site:lcsistemas.com.br", janela, "lcsistemas.com.br", "", f)   # tentou de novo mais tarde
    assert pesquisas == ["lcsistemas.com.br"]
