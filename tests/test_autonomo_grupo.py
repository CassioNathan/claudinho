"""Várias partes em paralelo e a junção dos branches, com git de verdade e um Claude de mentira."""
import subprocess
from pathlib import Path

import pytest

import autonomo


def git(pasta, *args):
    subprocess.run(["git", "-C", str(pasta), "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True,
                   capture_output=True)


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "comum.txt").write_text("linha 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(".claude/\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "inicio")
    return tmp_path


def claude_falso(repo, escrever):
    """Primeira rodada com -w: cria o worktree e o commit da parte (`escrever(titulo, pasta)`). No lugar (quem
    resolve conflito): `escrever("juntar", pasta)` e conclui o merge."""
    vistos = []

    def rodar(cmd, cwd, entrada):
        vistos.append(cmd)
        if "-w" in cmd:
            nome = cmd[cmd.index("-w") + 1]
            pasta = repo / ".claude" / "worktrees" / nome
            git(repo, "worktree", "add", "-q", "-b", f"worktree-{nome}", str(pasta))
            escrever(cmd[cmd.index("-n") + 1].removeprefix("🤖 "), pasta)
            git(pasta, "add", ".")
            git(pasta, "commit", "-qm", f"parte {nome}")
        else:
            escrever("juntar", Path(cwd))
            git(cwd, "add", ".")
            git(cwd, "commit", "-qm", "resolve conflito")
        return {"session_id": "s", "result": "Feito.\nSTATUS: PRONTO"}
    return rodar, vistos


def montar(repo, escrever, partes):
    avisos = []
    rodar, vistos = claude_falso(repo, escrever)
    g = autonomo.Grupo("tela de login", partes, repo, "proj", sid_pai="pai", rodar_claude=rodar,
                       decidir=lambda p: "PRONTO", avisar=lambda tipo, alvo, **extra: avisos.append((tipo, extra)))
    return g, avisos, vistos


PARTES = [{"titulo": "front", "plano": "fazer a tela"}, {"titulo": "back", "plano": "fazer a api"}]


def test_partes_em_paralelo_e_juntas_num_branch(repo):
    def escrever(titulo, pasta):
        (pasta / f"{titulo}.txt").write_text(titulo, encoding="utf-8")
    g, avisos, vistos = montar(repo, escrever, PARTES)
    g.rodar()
    assert g.estado == "pronta" and avisos[-1][0] == "grupo_pronto"
    assert all("--fork-session" in c for c in vistos)   # cada parte é uma cópia da conversa
    assert (g.integracao / "front.txt").exists() and (g.integracao / "back.txt").exists()
    assert len(avisos[-1][1]["mudancas"]["commits"]) >= 2
    assert sum(tipo == "parte_fim" for tipo, _ in avisos) == 2


def test_cada_parte_sabe_das_outras():
    t = autonomo.Grupo("x", PARTES, ".", "proj").partes[0]
    assert t.titulo == "front" and '"back"' in t.contexto


def test_conflito_vai_pra_um_subchat_que_resolve(repo):
    def escrever(titulo, pasta):
        texto = "linha 1 das duas\n" if titulo == "juntar" else f"linha 1 do {titulo}\n"
        (pasta / "comum.txt").write_text(texto, encoding="utf-8")
    g, avisos, vistos = montar(repo, escrever, PARTES)
    g.rodar()
    assert g.estado == "pronta", avisos
    assert (g.integracao / "comum.txt").read_text(encoding="utf-8") == "linha 1 das duas\n"
    assert any("-w" not in c and "--resume" not in c for c in vistos)   # quem resolveu: chat novo, no lugar


def test_parte_que_falha_fica_de_fora(repo):
    def escrever(titulo, pasta):
        if titulo == "back":
            raise RuntimeError("caiu")
        (pasta / f"{titulo}.txt").write_text(titulo, encoding="utf-8")
    g, avisos, _ = montar(repo, escrever, PARTES)
    g.rodar()
    assert g.estado == "pronta" and [t.titulo for t in g.faltou] == ["back"]
    assert not (g.integracao / "back.txt").exists()


def test_nenhuma_parte_pronta(repo):
    def escrever(titulo, pasta):
        raise RuntimeError("caiu")
    g, avisos, _ = montar(repo, escrever, PARTES)
    g.rodar()
    assert g.estado == "falhou" and avisos[-1][0] == "grupo_falhou"
