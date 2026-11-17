"""ClaudCorp: o escritório onde os chats do Claude Code e os agentes trabalham (a tela /escritorio).

Funcionários:
- cada chat do Claude Code é um funcionário; o cargo sobe com o tempo de casa: júnior → pleno → sênior;
- subagente (o "Agent" que um chat chama) é contratado pra uma coisa só: tarefa simples (pesquisar, procurar, ler)
  é estagiário; tarefa complexa ou de especialista é freela;
- o "fazer sozinho" (autonomo.py) e as partes dele também são freelas, na sala de reunião.

Nome e visual de cada um saem sorteados de um jeito fixo pela chave (o mesmo chat é sempre a mesma pessoa, sem
precisar guardar). Quando alguém termina, o resultado vai pra gaveta de relatórios (relatorios.json).
"""
import json
import random
import re
import threading
import time
from pathlib import Path

import skins

JUNIOR_ATE_S = 60 * 60          # chat com menos de 1 h de casa
PLENO_ATE_S = 4 * 60 * 60       # menos de 4 h; depois disso, sênior
MAX_RELATORIOS = 80
TEXTO_RELATORIO = 6000

NOMES = ["Rafa", "Bia", "Duda", "Léo", "Nina", "Caio", "Juju", "Tati", "Gabi", "Dani", "Lucas", "Marina", "Pedro",
         "Ana", "Bruno", "Carla", "Diego", "Fernanda", "Gustavo", "Helena", "Igor", "Joana", "Kaio", "Larissa",
         "Mateus", "Natália", "Otávio", "Paula", "Renato", "Sofia", "Thiago", "Vivi", "Wesley", "Yasmin", "Zeca",
         "Jorge", "Marcos", "Priscila", "Rodrigo", "Camila", "Felipe", "Aline", "Murilo", "Lívia", "Vitor"]
SOBRENOMES = ["Souza", "Silva", "Oliveira", "Santos", "Lima", "Costa", "Pereira", "Almeida", "Ribeiro", "Carvalho",
              "Gomes", "Martins", "Rocha", "Barbosa", "Teixeira", "Moreira", "Cardoso", "Nunes"]
APELIDOS = ["do Back-end", "do Front", "dos Testes", "do Deploy", "da Planilha", "do Café", "do Git", "da Revisão",
            "do Banco", "da Tela"]
# subagente de tarefa simples (pesquisar, procurar, ler): estagiário; o resto é freela
AGENTES_SIMPLES = {"explore", "claude-code-guide", "statusline-setup"}
SIMPLES = re.compile(r"\b(pesquis\w*|procur\w*|busc\w*|ach\w*|encontr\w*|list\w*|ler|l[eê]\w*|olh\w*|verific\w*|"
                     r"search\w*|find\w*|look\w*|explor\w*|read\w*|locat\w*)\b", re.I)


def nome_de(chave):
    r = random.Random("nome:" + str(chave))
    nome, sorte = r.choice(NOMES), r.random()
    if sorte < 0.2:
        return f"{'Seu' if nome[-1] not in 'aeiá' else 'Dona'} {nome} {r.choice(APELIDOS)}"
    if sorte < 0.6:
        return f"{nome} {r.choice(SOBRENOMES)}"
    return nome


def visual_de(chave):
    r = random.Random("visual:" + str(chave))
    visual, _ = skins.escolher_visual("aleatório", None, r)
    if visual.get("cor") == "laranja" and r.random() < 0.8:   # (os pacotes vêm laranja: mais cor no escritório)
        visual["cor"] = r.choice([c for c in skins.CORES if not skins.CORES[c].get("animada")])
    return visual


def sprite(visual):
    """O que a tela precisa pra desenhar o bonequinho: cores e os pixels dos adereços olhando pra cada lado."""
    cor = skins.CORES.get(visual.get("cor")) or skins.CORES["laranja"]
    itens = [visual[e] for e in skins.ESPACOS if visual.get(e) in skins.ADERECOS]
    lado = {f: [p for i in itens for p in skins.pixels(i, 0, f)] for f in (1, -1)}
    return {"corpo": skins.cor_do_corpo(visual.get("cor")), "olho": cor["olho"],
            "sapato": skins.cor_do_sapato(visual), "direita": lado[1], "esquerda": lado[-1]}


def cargo_do_chat(tempo_de_casa):
    if tempo_de_casa < JUNIOR_ATE_S:
        return "júnior"
    return "pleno" if tempo_de_casa < PLENO_ATE_S else "sênior"


def cargo_do_agente(tipo, descricao=""):
    if str(tipo or "").lower() in AGENTES_SIMPLES or SIMPLES.search(str(descricao or "")):
        return "estagiário"
    return "freela"


# conquistas da firma: (id, nome, como ganha) — a conta é feita em `conquistas_novas`
CONQUISTAS = [
    ("primeira", "Primeira entrega", "o primeiro relatório na gaveta"),
    ("dez", "Dez entregas", "10 relatórios entregues"),
    ("cinquenta", "Cinquentinha", "50 relatórios entregues"),
    ("cem", "Centenário", "100 relatórios entregues"),
    ("quinhentas", "Fábrica de software", "500 relatórios entregues"),
    ("estagiario", "Primeiro estagiário", "um agente de pesquisa entregou"),
    ("freela", "Primeiro freela", "um especialista entregou"),
    ("madrugada", "Coruja", "uma entrega entre meia-noite e 5 h"),
    ("lotado", "Casa cheia", "5 funcionários trabalhando ao mesmo tempo"),
    ("maratona", "Maratona", "um funcionário entregou 10 vezes no mesmo dia"),
]


class Escritorio:
    """O estado do escritório além das sessões (que o sessoes.py já guarda): subagentes trabalhando agora e a
    gaveta de relatórios. Tudo chamado da thread principal do Claudinho; a gravação é protegida por um lock."""

    def __init__(self, arquivo):
        self.arquivo = Path(arquivo)
        self.subagentes = {}      # agent_id → {chave, pai, projeto, tipo, descricao, cargo, desde}
        self.pendentes = {}       # session_id → [{tipo, descricao}] (o PreToolUse do Agent chega antes do Start)
        self.lock = threading.Lock()
        try:
            dados = json.loads(self.arquivo.read_text(encoding="utf-8"))
            self.relatorios = [r for r in dados if isinstance(r, dict)][:MAX_RELATORIOS]
        except (OSError, ValueError):
            self.relatorios = []
        self.arquivo_stats = self.arquivo.with_name("escritorio_stats.json")
        try:
            self.stats = json.loads(self.arquivo_stats.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.stats = {}
        for k, v in (("entregas", 0), ("por_chave", {}), ("mes", {}), ("dia", {}), ("conquistas", {})):
            self.stats.setdefault(k, v)
        if not self.arquivo_stats.exists() and self.relatorios:   # primeira vez: conta o que já está na gaveta
            for r in reversed(self.relatorios):
                self.contar(r)
            self.gravar_stats()

    # ---------- estatísticas e conquistas ----------
    def contar(self, r):
        """Uma entrega a mais: total, por funcionário, no mês e no dia (pro funcionário do mês e as conquistas)."""
        st, quando = self.stats, time.localtime(r["quando"])
        mes, dia = time.strftime("%Y-%m", quando), time.strftime("%Y-%m-%d", quando)
        st["entregas"] += 1
        st["por_chave"][r["chave"]] = st["por_chave"].get(r["chave"], 0) + 1
        st["mes"] = {mes: st["mes"].get(mes, {})}              # (só o mês de agora)
        st["mes"][mes][r["chave"]] = st["mes"][mes].get(r["chave"], 0) + 1
        st["dia"] = {dia: st["dia"].get(dia, {})}
        st["dia"][dia][r["chave"]] = st["dia"][dia].get(r["chave"], 0) + 1
        st.setdefault("cargo", {})[r["chave"]] = r["cargo"]
        self.conquistas_novas(r, quando)

    def ganhar(self, cid, agora=None):
        if cid not in self.stats["conquistas"]:
            self.stats["conquistas"][cid] = agora or time.time()
            return True
        return False

    def conquistas_novas(self, r=None, quando=None, trabalhando=0):
        n = self.stats["entregas"]
        for cid, minimo in (("primeira", 1), ("dez", 10), ("cinquenta", 50), ("cem", 100), ("quinhentas", 500)):
            if n >= minimo:
                self.ganhar(cid)
        if r:
            if r["cargo"] == "estagiário":
                self.ganhar("estagiario")
            if r["cargo"] == "freela":
                self.ganhar("freela")
            if quando and quando.tm_hour < 5:
                self.ganhar("madrugada")
            if max((self.stats["dia"].get(time.strftime("%Y-%m-%d", quando), {}) or {0: 0}).values()) >= 10:
                self.ganhar("maratona")
        if trabalhando >= 5 and self.ganhar("lotado"):
            self.gravar_stats()

    def gravar_stats(self):
        try:
            self.arquivo_stats.write_text(json.dumps(self.stats, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    def do_mes(self):
        """(chave, entregas) de quem mais entregou no mês, ou None."""
        mes = time.strftime("%Y-%m")
        contas = self.stats["mes"].get(mes) or {}
        return max(contas.items(), key=lambda kv: kv[1]) if contas else None

    def ficha(self, chave):
        """Tudo o que o escritório guarda de um funcionário: entregas (as que ainda estão na gaveta) e o total."""
        return {"relatorios": [r for r in self.relatorios if r["chave"] == chave],
                "entregas": self.stats["por_chave"].get(chave, 0)}

    # ---------- subagentes ----------
    def chamou_agente(self, sid, entrada):
        """PreToolUse do Agent/Task: guarda o que ele vai fazer, pro SubagentStart (que não manda a descrição)."""
        entrada = entrada if isinstance(entrada, dict) else {}
        self.pendentes.setdefault(sid, []).append({"tipo": str(entrada.get("subagent_type") or "general-purpose"),
                                                   "descricao": str(entrada.get("description") or "")[:120]})
        del self.pendentes[sid][:-8]

    def agente_comecou(self, d, agora=None):
        agora = time.time() if agora is None else agora
        sid, aid = str(d.get("session_id") or "?"), str(d.get("agent_id") or "")
        if not aid:
            return None
        tipo = str(d.get("agent_type") or "")
        fila = self.pendentes.get(sid) or []
        i = next((i for i, p in enumerate(fila) if not tipo or p["tipo"].lower() == tipo.lower()), 0 if fila else None)
        chamado = fila.pop(i) if i is not None else {}
        tipo = tipo or chamado.get("tipo") or "general-purpose"
        descricao = chamado.get("descricao") or ""
        a = {"chave": f"agente:{aid}", "id": aid, "pai": sid, "projeto": d.get("projeto") or "?", "tipo": tipo,
             "descricao": descricao, "cargo": cargo_do_agente(tipo, descricao), "desde": agora}
        self.subagentes[aid] = a
        return a

    def agente_terminou(self, d, agora=None):
        a = self.subagentes.pop(str(d.get("agent_id") or ""), None)
        if not a:
            return None
        texto = str(d.get("resultado") or "").strip()
        return self.guardar(a["chave"], a["cargo"], a["projeto"], a["descricao"] or a["tipo"], texto or "(sem texto)",
                            agora)

    # ---------- gaveta ----------
    def guardar(self, chave, cargo, projeto, titulo, texto, agora=None, mexeu=None):
        r = {"id": f"{int((agora or time.time()) * 1000)}-{random.randrange(1000)}", "chave": chave,
             "nome": nome_de(chave), "cargo": cargo, "projeto": projeto, "titulo": str(titulo or "")[:200],
             "texto": str(texto or "")[:TEXTO_RELATORIO], "quando": agora or time.time(),
             "mexeu": [str(m)[:200] for m in (mexeu or [])][:30]}
        with self.lock:
            self.contar(r)
            self.gravar_stats()
            self.relatorios.insert(0, r)
            del self.relatorios[MAX_RELATORIOS:]
            try:
                self.arquivo.parent.mkdir(parents=True, exist_ok=True)
                self.arquivo.write_text(json.dumps(self.relatorios, ensure_ascii=False), encoding="utf-8")
            except OSError:
                pass
        return r

    def apagar(self, rid=None):
        """Tira um relatório da gaveta (ou todos, sem `rid`)."""
        with self.lock:
            self.relatorios = [r for r in self.relatorios if rid is not None and r["id"] != rid]
            try:
                self.arquivo.write_text(json.dumps(self.relatorios, ensure_ascii=False), encoding="utf-8")
            except OSError:
                pass

    # ---------- a tela ----------
    def estado(self, sessoes, autonomas=(), agora=None):
        """O que a tela desenha: funcionários (com nome, cargo, onde está e o bonequinho), projetos (as mesas) e os
        relatórios. `sessoes`: Sessoes.ativas() (com "criada"); `autonomas`: as Tarefas do fazer sozinho."""
        agora = time.time() if agora is None else agora
        gente, vistos = [], {}
        auto = {f"auto-{t.id}": t for t in autonomas}

        def pessoa(chave, cargo, projeto, estado, fazendo, sala="mesa", extra=None):
            if chave not in vistos:
                vistos[chave] = sprite(visual_de(chave))
            gente.append(dict({"chave": chave, "nome": nome_de(chave), "cargo": cargo, "projeto": projeto,
                               "estado": estado, "fazendo": fazendo, "sala": sala}, **(extra or {})))
        for s in sessoes:
            sid = str(s.get("sid") or "")
            t = auto.get(sid)
            if t is not None:   # fazer sozinho: freela (as partes juntas, na sala de reunião)
                pessoa(f"chat:{sid}", "freela", t.projeto, s["estado"], s.get("fazendo") or t.titulo or "",
                       sala="reuniao" if t.titulo else "mesa", extra={"tarefa": (t.titulo or t.pedido)[:80]})
                continue
            if sid.startswith("auto-"):
                continue
            criada = s.get("criada") if s.get("criada") is not None else s.get("desde", agora)
            tempo = agora - criada
            trabalhou = s.get("trab_hoje", 0) if s.get("trab_dia") == time.strftime("%Y-%m-%d") else 0
            if s["estado"] == "trabalhando" and s.get("trab_desde"):
                trabalhou += max(0, agora - s["trab_desde"])
            pessoa(f"chat:{sid}", cargo_do_chat(tempo), s.get("projeto") or "?", s["estado"],
                   s.get("fazendo") or "", extra={"tarefa": (s.get("pedido") or "")[:80], "sid": sid,
                                                  "assunto": s.get("assunto") or s.get("pedido") or "",
                                                  "trabalhou_s": int(trabalhou), "casa_s": int(tempo)})
        for a in self.subagentes.values():
            if agora - a["desde"] > 3 * 60 * 60:   # subagente que nunca avisou que acabou: some depois de 3 h
                continue
            pessoa(a["chave"], a["cargo"], a["projeto"], "trabalhando", a["descricao"] or a["tipo"],
                   extra={"tarefa": a["descricao"], "chefe": nome_de(f"chat:{a['pai']}")})
        for r in self.relatorios[:30]:   # quem já entregou relatório (e pode nem estar mais aqui) também tem rosto
            if r["chave"] not in vistos:
                vistos[r["chave"]] = sprite(visual_de(r["chave"]))
        projetos = sorted({g["projeto"] for g in gente if g["sala"] == "mesa"})
        self.conquistas_novas(trabalhando=sum(g["estado"] == "trabalhando" for g in gente))
        do_mes = self.do_mes()
        if do_mes and do_mes[0] not in vistos:
            vistos[do_mes[0]] = sprite(visual_de(do_mes[0]))
        ganhas = self.stats["conquistas"]
        firma = {"entregas": self.stats["entregas"],
                 "conquistas": [{"id": c, "nome": n, "como": como, "quando": ganhas.get(c)} for c, n, como in CONQUISTAS],
                 "do_mes": {"chave": do_mes[0], "nome": nome_de(do_mes[0]), "entregas": do_mes[1],
                            "cargo": self.stats.get("cargo", {}).get(do_mes[0], "")} if do_mes else None}
        return {"funcionarios": gente, "projetos": projetos, "sprites": vistos, "relatorios": self.relatorios[:30],
                "agora": agora, "firma": firma}
