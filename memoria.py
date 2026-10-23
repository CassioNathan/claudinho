"""Memória do Claudinho num SQLite (~/.claudinho/claudinho.db): piadas e notas, avisos do dia e conversa.

Por que SQLite: um arquivo só, já vem no Python, consulta rápida e organizada.

Mudar a estrutura no futuro: NÃO edite as migrações antigas. Acrescente uma nova no fim de MIGRACOES;
ela roda sozinha uma vez em cada PC (o número da versão fica no próprio banco, em PRAGMA user_version).

Cada piada guarda o contexto em que saiu (programa, categoria, modo, alvo, música, hora). É isso que
permite buscar "piadas que ele curtiu nesse tipo de situação" (o RAG leve de `exemplos`).
"""
import json
import sqlite3
import threading
import time
from pathlib import Path

MIGRACOES = [
    # 1: estrutura inicial
    """
    CREATE TABLE piadas (
        id          INTEGER PRIMARY KEY,
        texto       TEXT NOT NULL,
        origem      TEXT,              -- haiku, banco, musica
        modelo      TEXT,              -- frase-modelo do banco (pra nota valer pra frase toda)
        assunto     TEXT,              -- do que fala (o Haiku informa)
        categoria   TEXT,              -- ide, discord, navegador... (programa em foco)
        app         TEXT,              -- exe em foco
        alvo        TEXT,              -- atividade, mouse, claudinho
        maldoso     INTEGER DEFAULT 0,
        tdah        INTEGER DEFAULT 0,
        musica      TEXT,
        criado_em   TEXT DEFAULT (datetime('now', 'localtime')),
        nota        INTEGER,           -- 1 boa, -1 ruim, NULL sem avaliação
        avaliado_em TEXT
    );
    CREATE INDEX piadas_criado ON piadas(criado_em);
    CREATE INDEX piadas_nota ON piadas(nota);
    CREATE TABLE avisos (
        id        INTEGER PRIMARY KEY,
        data      TEXT NOT NULL,       -- AAAA-MM-DD
        hora      TEXT,
        projeto   TEXT,
        pedido    TEXT,
        criado_em TEXT DEFAULT (datetime('now', 'localtime'))
    );
    CREATE INDEX avisos_data ON avisos(data);
    CREATE TABLE conversa (
        id        INTEGER PRIMARY KEY,
        numero    INTEGER NOT NULL,    -- muda a cada "Nova conversa"
        quem      TEXT NOT NULL,       -- eu, claudinho
        texto     TEXT NOT NULL,
        criado_em TEXT DEFAULT (datetime('now', 'localtime'))
    );
    CREATE TABLE meta (chave TEXT PRIMARY KEY, valor TEXT);
    """,
]


class Memoria:
    def __init__(self, caminho):
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.caminho, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.trava = threading.Lock()
        self.migrar()
        self.importar_json_antigo()

    # ---------- infraestrutura ----------
    def migrar(self):
        with self.trava, self.db:
            versao = self.db.execute("PRAGMA user_version").fetchone()[0]
            for numero, sql in enumerate(MIGRACOES[versao:], start=versao + 1):
                self.db.executescript(sql)
                self.db.execute(f"PRAGMA user_version = {numero}")

    def _exec(self, sql, args=()):
        with self.trava, self.db:
            return self.db.execute(sql, args)

    def _todos(self, sql, args=()):
        with self.trava:
            return self.db.execute(sql, args).fetchall()

    def meta(self, chave, padrao=None):
        linha = self._todos("SELECT valor FROM meta WHERE chave = ?", (chave,))
        return json.loads(linha[0]["valor"]) if linha else padrao

    def guardar_meta(self, chave, valor):
        self._exec("INSERT INTO meta(chave, valor) VALUES(?, ?) "
                   "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor", (chave, json.dumps(valor)))

    # ---------- piadas ----------
    def registrar_piada(self, texto, origem, modelo=None, assunto="", contexto=None):
        c = contexto or {}
        cur = self._exec(
            "INSERT INTO piadas(texto, origem, modelo, assunto, categoria, app, alvo, maldoso, tdah, musica) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (texto, origem, modelo, assunto or None, c.get("categoria"), c.get("app"), c.get("alvo"),
             int(bool(c.get("maldoso"))), int(bool(c.get("tdah"))), c.get("musica")))
        return cur.lastrowid

    def avaliar(self, piada_id, nota):
        self._exec("UPDATE piadas SET nota = ?, avaliado_em = datetime('now', 'localtime') WHERE id = ?",
                   (nota, piada_id))

    def piadas_recentes(self, n=25):
        return [r["texto"] for r in reversed(self._todos("SELECT texto FROM piadas ORDER BY id DESC LIMIT ?", (n,)))]

    def assuntos_recentes(self, n=8):
        return [r["assunto"] for r in self._todos(
            "SELECT assunto FROM piadas WHERE assunto IS NOT NULL ORDER BY id DESC LIMIT ?", (n,))]

    def modelos_recentes(self, n=40):
        return [r["modelo"] for r in self._todos(
            "SELECT modelo FROM piadas WHERE modelo IS NOT NULL ORDER BY id DESC LIMIT ?", (n,))]

    def textos_avaliados(self, n=60):
        return [r["texto"] for r in self._todos(
            "SELECT texto FROM piadas WHERE nota IS NOT NULL ORDER BY avaliado_em DESC LIMIT ?", (n,))]

    def notas_por_modelo(self):
        return {r["modelo"]: r["soma"] for r in self._todos(
            "SELECT modelo, SUM(nota) AS soma FROM piadas WHERE modelo IS NOT NULL AND nota IS NOT NULL "
            "GROUP BY modelo")}

    def exemplos(self, nota, categoria=None, maldoso=False, tdah=False, n=6):
        """RAG leve: piadas com essa nota, priorizando as do mesmo tipo de situação
        (mesma categoria de programa, mesmo modo maldoso/TDAH) e depois as mais recentes."""
        return [r["texto"] for r in self._todos(
            "SELECT texto FROM piadas WHERE nota = ? "
            "ORDER BY (categoria IS ?) + (maldoso = ?) + (tdah = ?) DESC, avaliado_em DESC LIMIT ?",
            (nota, categoria, int(maldoso), int(tdah), n))]

    def resumo(self):
        """Números do aprendizado (pra mostrar ou conferir)."""
        r = self._todos("SELECT COUNT(*) AS total, SUM(nota = 1) AS boas, SUM(nota = -1) AS ruins FROM piadas")[0]
        return dict(r)

    # ---------- avisos (memória do dia) ----------
    def registrar_aviso(self, projeto, pedido):
        self._exec("INSERT INTO avisos(data, hora, projeto, pedido) VALUES(?, ?, ?, ?)",
                   (time.strftime("%Y-%m-%d"), time.strftime("%H:%M"), projeto, pedido))

    def avisos_de(self, data):
        return [dict(r) for r in self._todos(
            "SELECT data, hora, projeto, pedido FROM avisos WHERE data = ? ORDER BY id", (data,))]

    # ---------- conversa ----------
    def conversa_atual(self):
        return self.meta("conversa_atual", 1)

    def registrar_mensagem(self, quem, texto):
        self._exec("INSERT INTO conversa(numero, quem, texto) VALUES(?, ?, ?)", (self.conversa_atual(), quem, texto))

    def ultima_resposta(self):
        linha = self._todos("SELECT texto FROM conversa WHERE numero = ? AND quem = 'claudinho' "
                            "ORDER BY id DESC LIMIT 1", (self.conversa_atual(),))
        return linha[0]["texto"] if linha else ""

    def conversa_velha(self, max_perguntas):
        """A conversa atual começou noutro dia ou já teve perguntas demais (cada mensagem relê o histórico todo)."""
        linha = self._todos("SELECT MIN(criado_em) AS inicio, SUM(quem = 'eu') AS perguntas FROM conversa "
                            "WHERE numero = ?", (self.conversa_atual(),))[0]
        if not linha["inicio"]:
            return False
        return linha["inicio"][:10] != time.strftime("%Y-%m-%d") or linha["perguntas"] >= max_perguntas

    def fim_da_conversa(self, numero, n=4):
        """As últimas `n` mensagens de uma conversa, da mais antiga pra mais nova."""
        linhas = self._todos("SELECT quem, texto FROM conversa WHERE numero = ? ORDER BY id DESC LIMIT ?", (numero, n))
        return [(l["quem"], l["texto"]) for l in reversed(linhas)]

    def nova_conversa(self):
        self.guardar_meta("conversa_atual", self.conversa_atual() + 1)
        self.guardar_meta("session_id", None)

    # ---------- dados antigos (JSON) ----------
    def importar_json_antigo(self):
        """Uma vez só: traz o estado.json e o avaliacoes.json pro banco e renomeia os dois (.importado)."""
        if self.meta("importou_json"):
            return
        pasta = self.caminho.parent
        estado = _ler(pasta / "estado.json", {})
        avaliacoes = _ler(pasta / "avaliacoes.json", [])
        avaliadas = set()
        for a in avaliacoes:
            pid = self.registrar_piada(a["texto"], a.get("origem"), a.get("modelo"),
                                       contexto={"maldoso": a.get("maldoso"), "tdah": a.get("tdah")})
            self._exec("UPDATE piadas SET nota = ?, avaliado_em = ?, criado_em = ? WHERE id = ?",
                       (a["nota"], a.get("data"), a.get("data"), pid))
            avaliadas.add(a["texto"])
        for texto in estado.get("piadas_recentes", []):
            if texto not in avaliadas:
                self.registrar_piada(texto, None)
        for aviso in estado.get("dia", []):
            self._exec("INSERT INTO avisos(data, hora, projeto, pedido) VALUES(?, ?, ?, ?)",
                       (aviso.get("data"), aviso.get("hora"), aviso.get("projeto"), aviso.get("pedido")))
        for m in estado.get("historico", []):
            self.registrar_mensagem("eu" if m["quem"] == "eu" else "claudinho", m["texto"])
        self.guardar_meta("session_id", estado.get("session_id"))
        self.guardar_meta("importou_json", True)
        for nome in ("estado.json", "avaliacoes.json"):
            if (pasta / nome).exists():
                (pasta / nome).replace(pasta / f"{nome}.importado")


def _ler(caminho, padrao):
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except Exception:
        return padrao
