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
