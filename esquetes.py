"""Esquetes de idle: de vez em quando, parado e sem nada pra fazer, o Claudinho apronta alguma.

Cada esquete tem duração (s), falas de começo e de fim (sorteia uma; lista vazia = calado)
e o que o desenho faz (o desenho mora no claudinho.pyw, que olha o nome da esquete)."""
import random

ESQUETES = {
    "ideia": {  # o fluxo completo: tem a ideia, pensa, trabalha no notebook e conta como foi (ou não foi)
        "duracao": 14, "notebook": (0.15, 0.92), "pensa_ate": 0.15, "emoji_inicio": "ideia",
        "inicio": ["Tive uma ideia!", "Pera… tive uma ideia.", "Ó, ó, tive uma ideia!"],
        "fim": [],  # o fim sai de resultado_da_ideia()
    },
    "inseto": {  # aparece um bichinho perto dele: ele vai lá e come (o claudinho.pyw cuida das fases)
        "duracao": 22,  # se não pegar até lá, o bicho foge
        "inicio": ["Opa… um bug!", "Ó lá um bug!", "Peraí… isso é um bug?"],
        "fim": ["Removi um bug 😄", "Bug removido. Delicioso. 😋", "Menos um bug em produção 😄",
                "Removi um bug 😄 (sem nem abrir o código)"],
        "fugiu": ["Fugiu… agora é feature.", "Escapou. Vou abrir uma issue.", "Não consegui reproduzir. 🤷"],
    },
    "deploy": {  # saca o notebook do nada e digita feito louco
        "duracao": 7, "notebook": True,
        "inicio": ["Calma, vou só fazer um deploy rapidinho.",
                   "Pera, deixa eu subir uma coisinha pra produção.",
                   "Rapidinho, só um hotfix."],
        "fim": ["Pronto. Em produção. Sexta-feira, 17h50. 😎",
                "Deploy feito. Se cair, não fui eu.",
                "Subiu! Testei? Não. Mas subiu.",
                "Hotfix no ar. Agora é rezar."],
    },
    "push_force": {  # notebook + gotinha de suor
        "emoji_fim": "suor", "duracao": 6, "notebook": True,
        "inicio": ["Só um git push --force rapidinho…",
                   "Vou só dar um rebase aqui, coisa simples."],
        "fim": ["…ninguém viu isso, ok?",
                "Pronto, reescrevi a história. Literalmente.",
                "Conflito? Que conflito? Resolvi apagando."],
    },
    "cafe": {  # caneca com fumacinha, dá uns goles
        "emoji_inicio": "cafe", "duracao": 9,
        "inicio": ["Pausa pro café ☕", "Café. Agora. Urgente.", "Hora do cafezinho."],
        "fim": ["Pronto, agora compilo mais rápido.", "Ahh… voltei a ser gente.",
                "Café tomado, bugs avisados."],
    },
    "cochilo": {  # olhinho fechado, respirando devagar, zzz subindo
        "emoji_inicio": "zzz", "duracao": 12,
        "inicio": [],
        "fim": ["Hã? Eu? Dormindo? Tava só fechando os olhos pra pensar.",
                "Não dormi, tava em modo de economia de energia.",
                "…acordei. Perdi algum deploy?"],
    },
    "alongar": {  # bracinhos pra cima, se esticando
        "duracao": 4,
        "inicio": ["Aaaaah… alongamento!", "Ai, as costas…"],
        "fim": [],
    },
    "danca": {  # pulinho com bracinhos alternando (com notinhas se tiver música)
        "emoji_inicio": "nota", "duracao": 6,
        "inicio": ["♪ Dancinha de quem passou nos testes ♪", "Testes verdes! ♪", "♪ Build passou, build passou ♪"],
        "inicio_musica": ["♪ Essa é boa! ♪", "Ó a música! ♪", "♪ Não resisto ♪"],
        "fim": [],
    },
}


# o fim da "ideia": dá certo na maioria das vezes, mas nem sempre
FEITOS = ["um app novo", "um site", "um sistema inteiro", "uma API", "um SaaS de R$ 9,90 por mês",
          "mais um framework JavaScript", "um app de lista de tarefas (o 47º)", "um ERP. Sozinho. Em 10 segundos",
          "um bot que faz piada de você", "um mascote pro meu mascote"]
SUCESSOS = ["Pronto, fiz {feito}! 🚀", "Fiz {feito}. Ninguém pediu, mas tá aí.", "Pronto: {feito}. Próxima unicórnio. 🦄",
            "Corrigi um bug!", "Corrigi 3 bugs. Achei 5. Saldo positivo? Não.", "Refatorei tudo. Funciona igual, mas agora é bonito."]
FRACASSOS = ["Acabaram meus tokens kkkk", "Tentei corrigir e criei outro bug.", "Deu erro. Vou chamar de feature.",
             "Funcionou na minha máquina. Só na minha.", "Apaguei o node_modules e agora tudo pesa 2 GB a menos. E não roda.",
             "Esqueci de salvar. Recomeço amanhã.", "Fiz {feito}, mas era um bug com interface."]


def resultado_da_ideia():
    """(fala, emoji) do fim da esquete 'ideia': ~65% dá certo."""
    if random.random() < 0.65:
        return random.choice(SUCESSOS).format(feito=random.choice(FEITOS)), random.choice(["check", "fogo"])
    return random.choice(FRACASSOS).format(feito=random.choice(FEITOS)), random.choice(["bug", "suor"])


# o bichinho da esquete "inseto" (joaninha vista de cima, cabeça pra direita), dois quadros de perninha
INSETO = [
    ["L.L.L..", ".RRRRL.", "RORORHL", ".RRRRL.", "L.L.L.."],
    [".L.L.L.", ".RRRRL.", "RORORHL", ".RRRRL.", ".L.L.L."],
]
CORES_INSETO = {"R": "#d1453b", "O": "#1f1e1d", "H": "#1f1e1d", "L": "#3a3936"}


def final(nome):
    """(fala, emoji) do fim da esquete; qualquer um dos dois pode ser None."""
    if nome == "ideia":
        return resultado_da_ideia()
    return fala(nome, "fim"), ESQUETES[nome].get("emoji_fim")


def sortear(ultima=None, musica_tocando=False):
    """Nome de uma esquete (evita repetir a última; a ideia é a mais comum; com música, a dança aparece mais)."""
    nomes = [n for n in ESQUETES if n != ultima]
    pesos = [3 if n == "ideia" or (n == "danca" and musica_tocando) else 1 for n in nomes]
    return random.choices(nomes, pesos)[0]


def fala(nome, momento, musica_tocando=False):
    """Fala de 'inicio' ou 'fim' da esquete, ou None se ela fica calada."""
    e = ESQUETES[nome]
    opcoes = e.get("inicio_musica") if momento == "inicio" and musica_tocando and e.get("inicio_musica") else e[momento]
    return random.choice(opcoes) if opcoes else None
