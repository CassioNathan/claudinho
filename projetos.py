"""Abrir um programa (IntelliJ, VS Code…) já num projeto: "abre o IntelliJ no LC Pedir".

Acha a pasta do projeto pelo nome (aproximado) só dentro das pastas que o chat lê sem perguntar (painel → Privacidade),
abre o programa nela e espera a janela do projeto aparecer, pra próxima etapa (rodar, compilar) já achar a janela.
Não roda comando nem passa outro argumento além da pasta."""
import json
import os
from pathlib import Path

import programas
import sistema

MARCAS = ("pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "package.json", ".idea", ".vscode",
          "pyproject.toml", "Cargo.toml", "go.mod", ".git")
PULAR = {"node_modules", ".git", ".idea", ".vscode", "build", "dist", "target", "out", ".gradle", "venv", ".venv",
         "__pycache__", "graphify-out", "bin", "obj"}


def pastas_liberadas():
    try:
        cfg = json.loads((sistema.DADOS / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    return [Path(p) for p in cfg.get("pastas_leitura") or [] if Path(p).is_dir()]


def do_claude():
    """Os projetos que o Claude Code (no terminal ou no app Claude) já abriu: as chaves de "projects" do ~/.claude.json.
    Sem as pastas temporárias do app e sem repetir a mesma pasta escrita de outro jeito (D:/x e D:\\x)."""
    try:
        dados = json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    vistas, lista = set(), []
    for bruto in dados.get("projects") or {}:
        pasta = Path(os.path.normpath(bruto))
        chave = str(pasta).lower()
        if (chave in vistas or pasta == Path.home() or "scratch-workspaces" in chave
                or "\\appdata\\local\\temp" in chave or not pasta.is_dir()):
            continue
        vistas.add(chave)
        lista.append(pasta)
    return sorted(lista, key=lambda p: str(p).lower())


def dentro(pasta, raizes):
    """A pasta é uma das raízes ou fica dentro de alguma (sem diferenciar maiúscula, como o Windows)."""
    alvo = str(Path(pasta)).lower().rstrip("\\")
    return any(alvo == r or alvo.startswith(r + "\\") for r in (str(Path(x)).lower().rstrip("\\") for x in raizes))


def eh_projeto(pasta):
    return any((pasta / m).exists() for m in MARCAS) or any(pasta.glob("*.sln"))


def _pastas(raiz, fundo=3):
    """As pastas até `fundo` níveis abaixo da raiz, pulando as de build/dependência."""
    fila = [(raiz, 0)]
    while fila:
        pasta, nivel = fila.pop(0)
        if nivel:
            yield pasta
        if nivel < fundo:
            try:
                filhas = sorted(p for p in pasta.iterdir() if p.is_dir() and p.name not in PULAR
                                and not p.name.startswith("."))
            except OSError:
                continue
            fila += [(p, nivel + 1) for p in filhas]


def achar(nome, n=6):
    """[(pontos, pasta, é_projeto)] das pastas que parecem com o nome, da melhor pra pior."""
    achados = []
    for raiz in pastas_liberadas():
        for pasta in _pastas(raiz):
            pontos = programas.pontuar(nome, pasta.name)
            if pontos >= 0.72:
                achados.append((pontos + (0.04 if eh_projeto(pasta) else 0), pasta, eh_projeto(pasta)))
    achados.sort(key=lambda t: (-t[0], len(str(t[1]))))
    return achados[:n]


def _dentro_das_liberadas(pasta):
    pasta = pasta.resolve()
    return any(pasta == r.resolve() or r.resolve() in pasta.parents for r in pastas_liberadas())


def _janela_do_projeto(exes, pasta):
    import janelas
    alvo = programas.normalizar(pasta.name)
    for j in janelas.listar():
        if j["exe"] in exes and alvo and alvo in programas.normalizar(j["titulo"]):
            return j
    return None


def abrir(programa, projeto, espera=120):
    """Abre o programa na pasta do projeto e espera a janela. Devolve o que fez (ou o que falta), em texto."""
    import abrir as _abrir
    achados = programas.achar(programa)
    if not achados:
        return f"não achei nenhum programa parecido com '{programa}' instalado"
    item = achados[0][1]
    if programas.esta_bloqueado(item):
        return f"{item['nome']} está bloqueado no painel (Programas): não abro nem mexo nele"
    if not item["atalho"]:
        return f"{item['nome']} é app da Loja: não dá pra abrir ele numa pasta"
    caminho = Path(projeto)
    if caminho.is_absolute() and caminho.is_dir():
        if not _dentro_das_liberadas(caminho):
            return f"{caminho} está fora das pastas liberadas no painel (Atalhos → Pastas): não abro"
        pasta = caminho
    else:
        candidatos = achar(projeto)
        if not candidatos:
            liberadas = ", ".join(str(p) for p in pastas_liberadas()) or "nenhuma"
            return (f"não achei nenhum projeto parecido com '{projeto}' nas pastas liberadas ({liberadas}). "
                    "Pergunte a ele qual é a pasta.")
        melhor = candidatos[0]
        # empate: nota parecida, ou subprojetos dentro da pasta escolhida ("LC Pedir" tem _API e _WEB dentro)
        empatados = [c for c in candidatos[1:] if melhor[0] - c[0] < 0.05 or melhor[1] in c[1].parents]
        if empatados:
            lista = "\n".join(f"- {c[1]}" + (" (projeto)" if c[2] else "") for c in [melhor, *empatados])
            return f"achei mais de uma pasta parecida com '{projeto}'; pergunte qual (ou passe o caminho):\n{lista}"
        pasta = melhor[1]
    exes = programas._exes(item)
    ja = _janela_do_projeto(exes, pasta) if exes else None
    if ja:
        _abrir.forcar_frente(ja["hwnd"])
        return f"{item['nome']} já estava aberto em {pasta.name}: trouxe pra frente (janela '{ja['titulo']}')"
    sistema.lancar(item["atalho"], f'"{pasta}"')  # fora do job do Claudinho: não fecha junto com ele
    if not exes:
        return f"mandei abrir {item['nome']} em {pasta}; não sei o nome da janela dele pra esperar"
    # espera a janela do projeto aparecer E o programa sossegar (CPU baixa), sem tempo fixo: PC rápido segue logo
    import janelas
    j, levou, pronta = janelas.esperar_pronta(lambda: _janela_do_projeto(exes, pasta), limite=espera)
    if not j:
        return (f"mandei abrir {item['nome']} em {pasta}, mas em {espera}s a janela do projeto não apareceu "
                "(pode estar carregando): confira com ver_tela antes de seguir")
    _abrir.forcar_frente(j["hwnd"])
    if pronta:
        return f"abri {item['nome']} em {pasta} e o projeto está pronto (levou {levou:.0f}s; janela '{j['titulo']}')"
    return (f"abri {item['nome']} em {pasta} (janela '{j['titulo']}'), mas depois de {levou:.0f}s ele ainda está "
            "carregando/indexando: dá pra seguir, mas confira com ver_tela")
