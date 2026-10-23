"""Banco de frases da Claudinho. Edite à vontade: {app}, {projeto} e {min} são preenchidos sozinhos."""
import random
import re
import time

# programa (.exe) -> categoria
PROGRAMAS = {
    "idea64.exe": "ide", "idea.exe": "ide", "netbeans64.exe": "ide", "netbeans.exe": "ide",
    "studio64.exe": "ide", "eclipse.exe": "ide", "bds.exe": "delphi",
    "code.exe": "vscode", "cursor.exe": "vscode",
    "discord.exe": "discord", "whatsapp.exe": "whatsapp", "whatsapp.root.exe": "whatsapp",
    "chrome.exe": "navegador", "msedge.exe": "navegador", "opera.exe": "navegador",
    "firefox.exe": "navegador", "brave.exe": "navegador",
    "claude.exe": "claude", "postman.exe": "postman", "docker desktop.exe": "docker",
    "windowsterminal.exe": "terminal", "cmd.exe": "terminal", "powershell.exe": "terminal",
    "mintty.exe": "terminal", "dbeaver.exe": "banco", "heidisql.exe": "banco",
    "mysqlworkbench.exe": "banco", "excel.exe": "planilha", "spotify.exe": "musica",
    "explorer.exe": "pastas", "ms-teams.exe": "reuniao", "teams.exe": "reuniao",
    "notion.exe": "notion", "teamviewer.exe": "suporte", "anydesk.exe": "suporte",
}

# palavra no título do navegador -> categoria
SITES = {
    "youtube": "youtube", "github": "github", "stack overflow": "stackoverflow",
    "localhost": "localhost", "127.0.0.1": "localhost", "chatgpt": "chatgpt",
    "claude": "claude", "gmail": "email", "outlook": "email", "linkedin": "linkedin",
    "instagram": "redes", "twitter": "redes", " / x": "redes", "netflix": "streaming",
    "jira": "tarefas", "trello": "tarefas", "swagger": "localhost",
}

NOMES = {
    "ide": "IntelliJ", "delphi": "Delphi", "vscode": "VS Code", "discord": "Discord",
    "whatsapp": "WhatsApp", "navegador": "navegador", "claude": "Claude", "postman": "Postman",
    "docker": "Docker", "terminal": "terminal", "banco": "banco de dados", "planilha": "Excel",
    "musica": "Spotify", "pastas": "Explorador", "reuniao": "Teams", "notion": "Notion",
    "suporte": "acesso remoto",
}

FRASES = {
    "ide": [
        "Esse {projeto} compila de primeira ou vai rolar uma reza antes?",
        "Se o Spring demorar mais pra subir, dá tempo de passar um café.",
        "Psiu… esse NullPointerException tá te olhando.",
        "Já deu Invalidate Caches and Restart hoje? É tradição.",
        "Código bonito esse. Quem escreveu? …ah, foi você. Então tá ótimo.",
        "{projeto} de novo? Vocês dois deviam assumir o namoro.",
    ],
    "delphi": [
        "Delphi aberto: respeita, que esse aí já viu o mundo acabar duas vezes.",
        "Um begin sem end é a coisa mais triste que existe.",
    ],
    "vscode": [
        "VS Code aberto com quantas extensões? Não precisa responder, eu sinto o peso.",
        "Ctrl+S nervoso detectado.",
        "Esse {projeto} tá ficando com cara de produção, hein.",
    ],
    "discord": [
        "Discord aberto… isso é reunião ou é fofoca?",
        "Se for pedido de ajuda no Discord, cobra em café.",
        "Respondendo mensagem ou só deixando no visto estratégico?",
    ],
    "whatsapp": [
        "WhatsApp aberto: é trabalho ou é o grupo da família mandando bom dia?",
        "Vou fingir que não tô vendo esse WhatsApp aí.",
        "Áudio de 4 minutos? Coragem.",
    ],
    "navegador": [
        "Quantas abas abertas? Eu contei e desisti.",
        "Pesquisando a solução ou procurando alguém que já passou pela mesma dor?",
    ],
    "youtube": [
        "YouTube aberto. Tutorial de 10 minutos ou vídeo de gato? Não julgo.",
        "Isso aí é estudo, né? Tô anotando que é estudo.",
    ],
    "github": [
        "GitHub aberto: hora de ver quem quebrou a main.",
        "Esse PR tá com cara de 'só uma mudancinha' de 40 arquivos.",
    ],
    "stackoverflow": [
        "Stack Overflow: onde a resposta certa sempre tem 3 votos e a errada tem 400.",
        "Copia, cola, reza. O ciclo da vida.",
    ],
    "localhost": [
        "Localhost aberto: funciona na sua máquina, então tá aprovado.",
        "Se der 500 eu não vi nada.",
        "Testando a API? Manda um GET de carinho pra ela.",
    ],
    "chatgpt": ["ChatGPT? Na minha frente? Tô magoado.", "Pode usar, mas eu sou mais fofo."],
    "claude": [
        "Olha só, o Claude trabalhando e eu aqui só de enfeite.",
        "Manda o Claude caprichar, que eu tô supervisionando.",
    ],
    "email": ["E-mail: o lugar onde as tarefas se reproduzem.", "Inbox zero é lenda urbana."],
    "linkedin": ["LinkedIn aberto… tá tudo bem aí? Quer conversar?"],
    "redes": ["Rolando o feed 'só um pouquinho', né?"],
    "streaming": ["Episódio rapidinho entre um deploy e outro? Respeito."],
    "tarefas": ["Mais um card pra coluna 'Fazendo' que nunca sai de lá."],
    "postman": [
        "Postman aberto: 200 OK é a frase mais romântica que existe.",
        "Esse header de autenticação aí tá certinho? Só conferindo.",
    ],
    "docker": ["Docker aberto: lá se foi metade da RAM.", "Se não funcionar, derruba e sobe de novo."],
    "terminal": [
        "Terminal aberto. Tô torcendo pra não ter um rm -rf aí.",
        "Linha de comando: modo hacker ativado.",
    ],
    "banco": [
        "Banco de dados aberto. Esse UPDATE tem WHERE, né? NÉ?",
        "SELECT * em produção? Corajoso.",
    ],
    "planilha": ["Excel aberto: alguém vai pedir um PROCV, eu sinto."],
    "musica": ["Que música é essa? Me deixa dançar também."],
    "pastas": ["Procurando arquivo? Aposto que tá em Downloads com nome 'final_v2_agora_vai'."],
    "reuniao": ["Reunião? Câmera desligada e cara de quem tá prestando atenção."],
    "notion": ["Organizando a vida no Notion. Agora só falta seguir."],
    "suporte": ["Acesso remoto: boa sorte, que o mouse do cliente é imprevisível."],
    "geral": [
        "Tô só passeando. Finge que eu não tô aqui.",
        "Bebeu água hoje? Bebe água.",
        "Postura! Endireita essas costas aí.",
        "Se travar, respira. Se continuar travado, reinicia.",
    ],
}

POR_TEMPO = [
    "{min} minutos no {app}. Que tal levantar e esticar as perninhas? Eu estico as minhas.",
    "Já são {min} minutos de {app} direto. Foco nível monge.",
    "{min} min no {app}… bebe uma água aí, por mim.",
]

POR_HORA = {
    "madrugada": ["Essa hora codando? O bug não vai fugir até amanhã, viu.",
                  "Já passou da hora de dormir. Eu sou um mascote, mas me preocupo."],
    "almoco": ["Hora do almoço! Programador alimentado é programador sem bug."],
    "sexta": ["Sexta à tarde: não sobe nada pra produção, pelo amor."],
}


# modo "comentário maldoso": zoeira de amigo, sem dó (mas sem baixaria)
MALDOSAS = {
    "ide": [
        "{projeto} de novo? Esse código já pediu medida protetiva contra você.",
        "Bonito esse código. Pena que não compila.",
        "Se gambiarra desse ponto, você já tava aposentado.",
        "Esse NullPointerException aí é seu filho, assume.",
        "Você não escreve código, você escreve futuros chamados de suporte.",
    ],
    "delphi": ["Delphi? Que corajoso. Ou que preso no passado, ainda não decidi."],
    "vscode": ["40 extensões instaladas e o código continua ruim. Interessante.",
               "Ctrl+S não salva o seu código de você mesmo, tá?"],
    "discord": ["Discord aberto e a task parada. Coincidência? Acho que não.",
                "Tá produzindo ou tá só reagindo com emoji?"],
    "whatsapp": ["WhatsApp aberto no horário de trabalho. Teu chefe ia amar ver isso.",
                 "Responde todo mundo no WhatsApp, mas o PR tá lá esperando review desde ontem."],
    "navegador": ["Quantas abas? Isso não é pesquisa, é acumulação.",
                  "Pesquisando como fazer o básico de novo, né?"],
    "youtube": ["YouTube 'pra estudar'. Sei. Eu também sou um mascote 'de produtividade'."],
    "github": ["Olhando o GitHub dos outros pra ver como se faz direito?",
               "Esse commit 'ajustes' aí explica muito sobre você."],
    "stackoverflow": ["Stack Overflow aberto. Engenheiro de Ctrl+C, Ctrl+V sênior.",
                      "Copiou a resposta de 2014 e espera que funcione. Fé é tudo."],
    "localhost": ["Funciona no localhost. Em produção é problema do você do futuro.",
                  "Testando na mão de novo? Teste automatizado é pra fracos, né?"],
    "chatgpt": ["ChatGPT na minha frente? Traíra."],
    "claude": ["Pedindo pro Claude fazer seu trabalho de novo? Eu vi, hein.",
               "O Claude trabalhando e você só olhando. Belo estagiário de IA você é."],
    "postman": ["Postman aberto: 500 Internal Server Error, sua especialidade."],
    "docker": ["Docker aberto e o PC já pediu socorro."],
    "terminal": ["Terminal aberto. Fingindo ser hacker pra quem?"],
    "banco": ["Esse UPDATE sem WHERE vai ser lembrado por gerações.",
              "Banco de dados aberto: a área do crime está isolada?"],
    "reuniao": ["Reunião que podia ser um e-mail, e você que podia estar codando."],
    "pastas": ["'final_v2_agora_vai_mesmo.zip'. Eu sei que tem um desses aí."],
    "geral": [
        "Tô aqui só pra registrar que você tá enrolando.",
        "Se produtividade fosse crime, você seria inocente.",
        "Eu sou só um mascote e mesmo assim trabalho mais que você.",
        "Essa postura aí é de quem já desistiu da coluna.",
    ],
}

MALDOSAS_POR_TEMPO = [
    "{min} minutos no {app} e ainda não resolveu? Impressionante, no mau sentido.",
    "{min} min de {app}. Se fosse fácil, já tinha terminado, né? Ah, é fácil.",
]


# memória do dia: {proj_dia} = projeto mais pedido hoje, {n_dia} = pedidos nele,
# {total_dia} = tarefas no dia, {ultimo_pedido} = o último pedido feito
DO_DIA = [
    "Já são {n_dia} pedidos no {proj_dia} hoje. Esse projeto virou bichinho de estimação?",
    "{total_dia} tarefas entregues pelo Claude hoje. Tô orgulhoso de vocês dois.",
    "Aquele \"{ultimo_pedido}\" ficou pronto, hein. Já testou?",
]
DO_DIA_MALDOSAS = [
    "{n_dia} pedidos no {proj_dia} hoje. Se acertasse de primeira, era um só.",
    "{total_dia} tarefas hoje e quem fez foi o Claude. Você só apertou Enter.",
    "\"{ultimo_pedido}\"… sério que precisou de IA pra isso?",
]


# modo TDAH: começa no programa ({app}) e foge do assunto
TDAH = [
    "Olhando esse {app} lembrei: polvo tem três corações. Você tem um, e ele tá todo no {app}.",
    "Esse {app}… sabia que abelha dança pra indicar caminho? Tipo um Git, mas com menos conflito.",
    "Quem decidiu que pizza é redonda e a caixa é quadrada? Enfim, belo {app}.",
    "Esse {app} me lembrou um pato. Não sei por quê. Patos são legais.",
    "Imagina um Ctrl+Z da vida real. Ia ser o maior app do mundo. Voltando ao {app}…",
    "Pinguim pede em casamento com pedrinha. Você podia pedir um café. Enfim, {app}.",
    "O {app} tá aberto e eu aqui pensando se peixe sente sede.",
    "Lembrei que o Sol é uma estrela média. Igual esse código. Mas brilha!",
    "Se o {app} fosse sabor de sorvete, seria flocos. Não me pergunte.",
    "Nuvem pesa toneladas e fica lá em cima. E o {app} travando com duas abas.",
    "Pensei em lasanha. Do nada. Ah, e o {app} tá aí, né.",
    "Será que formiga tem reunião de alinhamento? Parece que sim. Igual você no {app}.",
]


# o que está tocando: {musica}, {artista} e {app} são preenchidos sozinhos
MUSICA = [
    "Tocando {musica}, de {artista}. Bom gosto, hein. Posso pedir a próxima?",
    "{musica} no {app}? Agora o código sai no ritmo.",
    "Essa {musica} é trilha sonora oficial de deploy, já pode registrar.",
    "Se eu tivesse fone, tava ouvindo {musica} junto.",
    "{artista} de fundo e foco total. Respeito.",
]
MUSICA_MALDOSAS = [
    "{musica}, de {artista}? Agora entendi o estado desse código.",
    "Ouvindo {artista} no volume do bug: alto e sem controle.",
    "{musica} de novo? Seu algoritmo de recomendação desistiu de você.",
    "Com {musica} tocando eu também não conseguiria me concentrar, relaxa.",
]


def dados_do_dia(dia):
    if not dia:
        return None
    contagem = {}
    for a in dia:
        contagem[a["projeto"]] = contagem.get(a["projeto"], 0) + 1
    proj, n = max(contagem.items(), key=lambda kv: kv[1])
    ultimo = dia[-1]["pedido"]
    if len(ultimo) > 50:
        ultimo = ultimo[:50].rsplit(" ", 1)[0] + "…"
    return {"proj_dia": proj, "n_dia": n, "total_dia": len(dia), "ultimo_pedido": ultimo}


def categoria(janela):
    exe, titulo = janela.get("exe", ""), janela.get("titulo", "").lower()
    cat = PROGRAMAS.get(exe, "geral")
    if cat == "navegador":
        for chave, site in SITES.items():
            if chave in titulo:
                return site
    return cat


def projeto_do_titulo(janela):
    titulo = janela.get("titulo", "")
    if janela.get("exe") in ("code.exe", "cursor.exe"):
        partes = [p.strip() for p in re.split(r" [-–—] ", titulo)]
        return partes[-2] if len(partes) >= 2 else ""
    return re.split(r" [-–—] ", titulo)[0].strip()[:30]


def momento():
    agora = time.localtime()
    if agora.tm_hour >= 23 or agora.tm_hour < 5:
        return "madrugada"
    if 12 <= agora.tm_hour < 13:
        return "almoco"
    if agora.tm_wday == 4 and agora.tm_hour >= 16:
        return "sexta"
    return None


def sortear(opcoes, recentes, notas):
    """Sorteia evitando as recentes e usando as avaliações: nota negativa sai, positiva pesa mais."""
    livres = [o for o in opcoes if o not in recentes] or opcoes
    aprovadas = [o for o in livres if notas.get(o, 0) >= 0] or livres
    pesos = [1 + max(0, notas.get(o, 0)) for o in aprovadas]
    return random.choices(aprovadas, weights=pesos)[0]


def escolher(janela, minutos_no_app, recentes=(), maldoso=False, dia=(), tdah=False, notas=None,
             musica=None):
    """Monta um comentário a partir do banco. `janela` pode ser None; `dia` = avisos de hoje;
    `notas` = soma das avaliações boa/ruim de cada frase; `musica` = o que está tocando (ou None)."""
    notas = notas or {}
    cat = categoria(janela) if janela else "geral"
    so_tela = maldoso or tdah  # nesses modos a zoeira é sobre a tela, não sobre segundo plano
    if musica and musica.get("tocando") and random.random() < (0.06 if so_tela else 0.25):  # zoa a música
        modelo = sortear(MUSICA_MALDOSAS if maldoso else MUSICA, recentes, notas)
        return modelo, modelo.format(musica=musica["titulo"], artista=musica["artista"] or "artista desconhecido",
                                     app=musica["app"])
    if tdah and random.random() < 0.7:  # modo TDAH: parte do programa e viaja pra outro assunto
        modelo = sortear(TDAH, recentes, notas)
        return modelo, modelo.format(app=NOMES.get(cat, "computador") if janela else "computador")
    extras = dados_do_dia(dia)
    if extras and not so_tela and random.random() < 0.12:  # lembra do que foi feito hoje (pouco: vira bordão)
        do_dia = DO_DIA_MALDOSAS if maldoso else DO_DIA
        if extras["n_dia"] < 2:
            do_dia = [o for o in do_dia if "{n_dia}" not in o]
        if not extras["ultimo_pedido"]:
            do_dia = [o for o in do_dia if "{ultimo_pedido}" not in o]
        livres = [o for o in do_dia if o not in recentes and notas.get(o, 0) >= 0]
        if livres:
            modelo = sortear(livres, recentes, notas)
            return modelo, modelo.format(**extras)
    banco = MALDOSAS if maldoso else FRASES
    opcoes = list(banco.get(cat) or FRASES.get(cat, [])) * 2
    if minutos_no_app >= 45 and janela:
        opcoes += MALDOSAS_POR_TEMPO if maldoso else POR_TEMPO
    if momento() and not maldoso:
        opcoes += POR_HORA[momento()]
    opcoes += banco["geral"]
    projeto = projeto_do_titulo(janela) if janela else ""
    if not projeto:
        opcoes = [o for o in opcoes if "{projeto}" not in o]
    modelo = sortear(opcoes, recentes, notas)
    texto = modelo.format(app=NOMES.get(cat, cat.capitalize()), projeto=projeto, min=int(minutos_no_app))
    return modelo, texto
