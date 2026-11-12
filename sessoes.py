"""O que eu (o Claude Code deste PC) estou fazendo em cada janela: uma lista viva das sessões do Claude Code,
montada pelos avisos do hook (claudinho_notificar). Fica gravada em ~/.claudinho/sessoes.json pro MCP ler
(`minhas_sessoes`) e o painel mostrar.

Estados: "trabalhando" (recebeu pedido ou está usando ferramenta), "esperando" (parou pedindo permissão ou com
uma pergunta), "pronto" (terminou a rodada), "aberta" (abriu e ainda não fez nada). Sessão fechada sai da lista;
a que ficou sem notícia por VELHA_S também (o app fechado à força não manda o SessionEnd).
"""
import json
import time
from pathlib import Path

VELHA_S = 8 * 3600
TRAVADA_S = 20 * 60   # "trabalhando" sem notícia há tanto tempo: provavelmente fechou sem avisar

# a ferramenta do Claude Code em português, pra dizer o que estou fazendo agora
FERRAMENTAS = {
    "Read": "lendo {arquivo}", "Edit": "editando {arquivo}", "MultiEdit": "editando {arquivo}",
    "Write": "escrevendo {arquivo}", "NotebookEdit": "editando {arquivo}", "Grep": "procurando no código",
    "Glob": "procurando arquivos", "WebFetch": "lendo uma página", "WebSearch": "pesquisando na web",
    "Task": "com um ajudante", "Agent": "com um ajudante", "TodoWrite": "organizando as tarefas",
    "AskUserQuestion": "com uma pergunta pra você",
}


def o_que_faz(ferramenta, entrada):
    """"rodando os testes", "editando motores.py"… em poucas palavras."""
    entrada = entrada if isinstance(entrada, dict) else {}
    if ferramenta in ("Bash", "PowerShell"):
        desc = str(entrada.get("description") or "").strip().rstrip(".")
        return (desc[:1].lower() + desc[1:])[:80] if desc else "rodando um comando"
    arq = entrada.get("file_path") or entrada.get("notebook_path") or entrada.get("path") or ""
    arquivo = Path(str(arq)).name if arq else "um arquivo"
    modelo = FERRAMENTAS.get(ferramenta)
    if modelo:
        return modelo.format(arquivo=arquivo)
    if str(ferramenta).startswith("mcp__"):
        return "usando " + str(ferramenta).rsplit("__", 1)[-1].replace("_", " ")
    return f"usando {ferramenta}" if ferramenta else "trabalhando"


class Sessoes:
    def __init__(self, arquivo=None):
        self.arquivo = Path(arquivo) if arquivo else None
        self.por_id = {}

    def registrar(self, d, agora=None):
        """Um aviso do hook (o dict que chega em /aviso). Devolve a sessão atualizada (ou None se fechou)."""
        agora = time.time() if agora is None else agora
        sid = d.get("session_id") or d.get("pasta") or "?"
        evento = d.get("evento") or "fim"   # o aviso antigo do Stop não manda "evento"
        if evento == "fechou":
            self.por_id.pop(sid, None)
            self.gravar()
            return None
        s = self.por_id.setdefault(sid, {"sid": sid, "projeto": d.get("projeto") or "?", "pasta": d.get("pasta") or "",
                                         "estado": "aberta", "pedido": "", "fazendo": "", "desde": agora})
        s["projeto"] = d.get("projeto") or s["projeto"]
        s["pasta"] = d.get("pasta") or s["pasta"]
        if evento == "pedido":
            s.update(estado="trabalhando", pedido=" ".join(str(d.get("pedido") or "").split())[:200], fazendo="",
                     desde=agora)
        elif evento == "ferramenta":
            s.update(estado="trabalhando", fazendo=o_que_faz(d.get("ferramenta"), d.get("entrada")))
        elif evento in ("espera", "permissao"):
            s.update(estado="esperando", fazendo=str(d.get("fazendo") or d.get("mensagem") or "")[:120])
        elif evento == "fim":
            s.update(estado="pronto", fazendo="", resumo=str(d.get("resumo") or "")[:200])
            if d.get("pedido") and not s["pedido"]:
                s["pedido"] = " ".join(str(d["pedido"]).split())[:200]
        s["visto"] = agora
        self.gravar()
        return s

    def ativas(self, agora=None):
        """As sessões que valem mostrar, as que precisam de você primeiro, depois as trabalhando."""
        agora = time.time() if agora is None else agora
        for sid in [k for k, s in self.por_id.items() if agora - s.get("visto", 0) > VELHA_S]:
            self.por_id.pop(sid)
        ordem = {"esperando": 0, "trabalhando": 1, "pronto": 2, "aberta": 3}
        lista = []
        for s in self.por_id.values():
            s = dict(s)
            if s["estado"] == "trabalhando" and agora - s.get("visto", 0) > TRAVADA_S:
                s["estado"] = "parada"
            lista.append(s)
        return sorted(lista, key=lambda s: (ordem.get(s["estado"], 4), -s.get("visto", 0)))

    def trabalhando(self, agora=None):
        return [s for s in self.ativas(agora) if s["estado"] == "trabalhando"]

    def descrever(self, agora=None):
        """Em primeira pessoa, uma linha por janela (é o que o chat e a ferramenta `minhas_sessoes` usam)."""
        agora = time.time() if agora is None else agora
        linhas = []
        for s in self.ativas(agora):
            minutos = max(1, round((agora - s.get("desde", agora)) / 60))
            pedido = f" (pedido: \"{s['pedido'][:100]}\")" if s.get("pedido") else ""
            if s["estado"] == "esperando":
                linhas.append(f"- {s['projeto']}: parado esperando você" + (f": {s['fazendo']}" if s.get("fazendo") else "")
                              + pedido)
            elif s["estado"] == "trabalhando":
                linhas.append(f"- {s['projeto']}: trabalhando há {minutos} min" + (f", agora {s['fazendo']}"
                                                                                 if s.get("fazendo") else "") + pedido)
            elif s["estado"] == "pronto":
                linhas.append(f"- {s['projeto']}: terminei" + (f" ({s['resumo']})" if s.get("resumo") else "") + pedido)
            elif s["estado"] == "parada":
                linhas.append(f"- {s['projeto']}: sem notícia há um tempo (talvez a janela tenha fechado)" + pedido)
            else:
                linhas.append(f"- {s['projeto']}: aberta, sem pedido ainda")
        return "\n".join(linhas)

    def gravar(self):
        if not self.arquivo:
            return
        try:
            self.arquivo.write_text(json.dumps(list(self.por_id.values()), ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    @classmethod
    def ler(cls, arquivo):
        """Pra quem está fora do app (o MCP): a lista gravada."""
        s = cls()
        try:
            for item in json.loads(Path(arquivo).read_text(encoding="utf-8")):
                if isinstance(item, dict) and item.get("sid"):
                    s.por_id[item["sid"]] = item
        except (OSError, ValueError):
            pass
        return s
