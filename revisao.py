"""Peças do revisor do modo Júnior que não dependem da janela (e por isso dá pra testar sozinhas).

- `contexto_git`: o `git status` e o `git diff` do projeto, gerados aqui (o revisor não tem Bash: só lê arquivos).
- `comando_de_teste`: o comando de teste que a IA sugeriu, só se for um da lista branca, já como lista de argumentos.
- `rodar_teste`: roda esse comando sem shell, com tempo limite que derruba a árvore inteira de processos.
- `extrair_json`: o primeiro objeto JSON de um texto (o modelo às vezes escreve antes ou depois dele).
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)
LIMITE_TESTE_S = 15 * 60          # teste que passa disso é parado (e os processos filhos junto)
LIMITE_SAIDA = 3000               # da saída do teste, só o fim vai pro balão e pro chat
LIMITE_DIFF = 12000               # o diff que vai pro revisor (o resto ele lê nos arquivos)

# git que só lê: sem fsmonitor/hook/diff externo/textconv configurados no repositório (que rodariam código)
GIT_SEGURO = ["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=", "-c", "diff.external=",
              "-c", "core.pager=cat"]

# comandos de teste aceitos, exatamente assim (minúsculas, espaços normalizados) → programa e argumentos
TESTES = {
    "npm test": ["npm", "test"], "npm run test": ["npm", "run", "test"], "npm t": ["npm", "test"],
    "yarn test": ["yarn", "test"], "pnpm test": ["pnpm", "test"],
    "python -m pytest": ["python", "-m", "pytest"], "py -m pytest": ["py", "-m", "pytest"], "pytest": ["pytest"],
    "python -m unittest": ["python", "-m", "unittest"],
    "mvn test": ["mvn", "test"], "mvn -q test": ["mvn", "-q", "test"], "gradle test": ["gradle", "test"],
    "dotnet test": ["dotnet", "test"], "cargo test": ["cargo", "test"], "go test ./...": ["go", "test", "./..."],
}
# os wrappers do próprio projeto (mvnw, gradlew) vivem DENTRO do repositório: aceitos só pelo caminho conhecido
WRAPPERS = {"mvnw test": ("mvnw.cmd", ["test"]), "./mvnw test": ("mvnw.cmd", ["test"]),
            "gradlew test": ("gradlew.bat", ["test"]), "./gradlew test": ("gradlew.bat", ["test"])}


def extrair_json(texto):
    """O primeiro objeto JSON (dict) dentro do texto, ou None. Diferente de `\\{.*\\}`, não se perde quando
    o texto continua depois com outras chaves."""
    decodificador = json.JSONDecoder()
    texto = texto or ""
    i = texto.find("{")
    while i != -1:
        try:
            obj, _ = decodificador.raw_decode(texto, i)
            if isinstance(obj, dict):
                return obj
        except ValueError:
            pass
        i = texto.find("{", i + 1)
    return None


def _git(raiz, *args):
    try:
        r = subprocess.run(GIT_SEGURO + list(args), cwd=raiz, capture_output=True, timeout=30,
                           creationflags=SEM_JANELA)
        return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def contexto_git(raiz):
    """Status e diff do projeto pro revisor (texto; vazio se não for git). Sem --output, sem diff externo."""
    status = _git(raiz, "status", "--short", "--untracked-files=normal")
    diff = _git(raiz, "diff", "--no-ext-diff", "--no-textconv", "HEAD") or _git(raiz, "diff", "--no-ext-diff",
                                                                               "--no-textconv")
    if len(diff) > LIMITE_DIFF:
        diff = diff[:LIMITE_DIFF] + "\n… (diff cortado; leia os arquivos pra ver o resto)"
    return status.strip(), diff.strip()


def _normalizar(comando):
    return " ".join(str(comando or "").strip().lower().split())


def comando_de_teste(sugerido, raiz):
    """A lista de argumentos pra rodar o teste sugerido, ou None se ele não é um comando conhecido.
    O programa é procurado no PATH e nunca dentro da pasta do projeto (lá um `npm.cmd` plantado rodaria no lugar)."""
    chave = _normalizar(sugerido)
    raiz = Path(raiz).resolve()
    if chave in WRAPPERS:
        arquivo, args = WRAPPERS[chave]
        caminho = raiz / arquivo
        return [str(caminho)] + args if caminho.is_file() else None
    if chave not in TESTES:
        return None
    programa, *args = TESTES[chave]
    caminho = shutil.which(programa, path=os.environ.get("PATH", ""))
    if not caminho:
        return None
    caminho = Path(caminho).resolve()
    if caminho == raiz or raiz in caminho.parents:
        return None
    return [str(caminho)] + args


def _matar_arvore(processo):
    """No Windows, matar só o processo deixa os filhos (node, java…) segurando a saída: derruba a árvore toda."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(processo.pid)], capture_output=True,
                       creationflags=SEM_JANELA)
    else:
        processo.kill()


def _decodificar(bruto):
    try:   # npm, pytest… falam utf-8; o console do Windows fala na página de código dele
        return bruto.decode("utf-8")
    except UnicodeDecodeError:
        return bruto.decode("oem" if os.name == "nt" else "latin-1", "replace")


def rodar_teste(argumentos, raiz, limite=LIMITE_TESTE_S):
    """Roda o teste (lista de argumentos, sem shell). Devolve (situacao, codigo, saida):
    situacao = "passou" | "falhou" | "demorou" | "nao_rodou"."""
    try:
        processo = subprocess.Popen(argumentos, cwd=raiz, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    creationflags=SEM_JANELA)
    except OSError as e:
        return "nao_rodou", None, str(e)
    try:
        bruto, _ = processo.communicate(timeout=limite)
    except subprocess.TimeoutExpired:
        _matar_arvore(processo)
        try:
            bruto, _ = processo.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            bruto = b""
        return "demorou", None, _decodificar(bruto or b"")[-LIMITE_SAIDA:]
    saida = _decodificar(bruto or b"")[-LIMITE_SAIDA:]
    return ("passou" if processo.returncode == 0 else "falhou"), processo.returncode, saida
