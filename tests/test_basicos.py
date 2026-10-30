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


def test_janelas_do_plano_tira_as_resetadas():
    plano = {"rate_limits": {"five_hour": {"used_percentage": "40", "resets_at": time.time() + 3600},
                             "seven_day": {"used_percentage": 90, "resets_at": 1}}}
    janelas = consumo.janelas_do_plano(plano)
    assert list(janelas) == ["five_hour"] and janelas["five_hour"]["pct"] == 40
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
