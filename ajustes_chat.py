"""O que o chat pode mudar no Claudinho quando ele pede ("entra no modo júnior", "fala mais baixo", "fica parado").

Fica de fora (só no painel) o que é segurança ou privacidade: motor de IA, pastas liberadas, navegador, programas
bloqueados, atalhos e comandos que agem no PC, rotinas, "Sempre", WhatsApp, quem é ele (mestre), reconhecimento de
voz na nuvem. E alguns só andam pro lado seguro pelo chat: a faixa nos olhos só põe, o microfone, o "olhar a tela"
e guardar áudio só desligam. Tarefas, memória e visual têm ferramenta própria.
"""
import unicodedata

SIM = {"sim", "liga", "ligar", "ligado", "on", "true", "1", "ativa", "ativar", "ativado", "habilita", "habilitar"}
NAO = {"nao", "desliga", "desligar", "desligado", "off", "false", "0", "desativa", "desativar", "desativado",
       "desabilita", "desabilitar"}

# chave: (descrição, tipo, extra). tipo: bool | opcoes ({o que ele diz: valor}) | num ((mín, máx)) | texto | frequencia
AJUSTES = {
    "modo_junior": ("conferir sozinho o que eu fizer nos chats do Claude Code (modo Júnior)", "bool", None),
    "resumir_avisos": ("resumir em uma frase o aviso de chat que terminou (desligado: texto inteiro)", "bool", None),
    "permissao_pelo_balao": ("o Pode/Não dos chats do Claude Code no meu balão", "bool", None),
    "comentar_tela": ("piadas e comentários sobre a tela", "bool", None),
    "esquetes": ("esquetes à toa (café, cochilo…)", "bool", None),
    "modo_tdah": ("piadas no modo TDAH", "bool", None),
    "modo_avaliacao": ("botões boa/ruim nas piadas", "bool", None),
    "comentar_a_cada_minutos": ("de quanto em quanto tempo eu comento: bastante, normal, de vez em quando ou "
                                "\"A-B\" minutos", "frequencia", None),
    "chance_haiku": ("chance de olhar a tela de verdade na piada (0 a 1; o resto sai do banco de frases)", "num",
                     (0.0, 1.0)),
    "emojis": ("emojis subindo do meu lado", "bool", None),
    "iniciativa": ("puxar assunto quando importa (resumo do dia, pausa)", "bool", None),
    "personalidade": ("meu jeito: claudinho ou ultron", "opcoes", {"claudinho": "claudinho", "ultron": "ultron"}),
    "movimento": ("como eu ando: livre, horizontal (só de lado) ou parado", "opcoes",
                  {"livre": "livre", "solto": "livre", "horizontal": "horizontal", "de lado": "horizontal",
                   "parado": "parado", "quieto": "parado"}),
    "seguir_mouse_entre_monitores": ("ir pro monitor onde está o mouse", "bool", None),
    "jogo_canto": ("ir pro canto em jogo ou tela cheia", "bool", None),
    "tamanho": ("meu tamanho na tela, em % (30 a 100)", "num", (30, 100)),
    "borda": ("contorno em volta de mim", "bool", None),
    "borda_forca": ("quão visível é o contorno (10 a 100)", "num", (10, 100)),
    "aviso_segundos": ("quanto tempo o aviso fica na tela, em segundos (3 a 30)", "num", (3, 30)),
    "avisar_versao": ("avisar quando sair versão nova", "bool", None),
    "vendado": ("faixa nos olhos: não olho a tela (pelo chat só dá pra pôr)", "bool", "so_ligar"),
    "ver_tela": ("olhar a tela quando você pede (pelo chat só dá pra desligar)", "bool", "so_desligar"),
    "ver_musica": ("saber o que está tocando", "bool", None),
    "lembrancas": ("lembrar de conversas parecidas (busca no PC)", "bool", None),
    "memoria_auto": ("anotar sozinho fatos seus no fim da conversa", "bool", None),
    "aprender_fluxos": ("oferecer guardar como comando o que resolvi no PC", "bool", None),
    "chat_modelo": ("quem responde o chat", "opcoes", None),     # (as opções vêm do Claudinho)
    "chat_esforco": ("quanto eu penso antes de responder: low, medium, high, xhigh, max", "opcoes", None),
    "ollama_pensar": ("a IA local pensa antes de responder (mais certo, mais lento)", "bool", None),
    "voz_fala": ("responder falando", "bool", None),
    "so_fala": ("só fala: sem balão de texto", "bool", None),
    "voz_voz": ("qual voz eu uso", "voz", None),
    "voz_volume": ("volume da minha voz (0 a 100)", "num", (0, 100)),
    "voz_tom": ("quão agudo eu falo (0 a 40)", "num", (0, 40)),
    "voz": ("ouvir o microfone esperando você me chamar (pelo chat só dá pra desligar)", "bool", "so_desligar"),
    "voz_saudacao": ("cumprimentar quando a conversa por voz começa", "bool", None),
    "voz_comandos": ("comandos rápidos de voz sem IA (pausa, próxima, abre X)", "bool", None),
    "voz_pausar_midia": ("pausar a música enquanto te ouço", "bool", None),
    "voz_continua": ("continuar ouvindo depois de responder", "bool", None),
    "voz_interromper": ("parar de falar quando você diz \"para\"", "bool", None),
    "voz_roteador": ("adivinhar comando de voz que não bateu certinho", "bool", None),
    "voz_sem_comando": ("frase de voz que não é comando: chat (manda pro chat) ou estrito (digo que não sei)",
                        "opcoes", {"chat": "chat", "estrito": "estrito"}),
    "voz_sons": ("sons de quando começo e paro de ouvir", "bool", None),
    "voz_detector": ("detector treinado do meu nome", "bool", None),
    "voz_limpar": ("filtro de ruído do microfone", "bool", None),
    "voz_travar_nivel": ("ignorar voz baixa ao fundo (TV, gente)", "bool", None),
    "voz_guardar_chamadas": ("guardar o áudio das chamadas pro treino (pelo chat só dá pra desligar)", "bool",
                             "so_desligar"),
    "voz_silencio": ("segundos calado até eu enviar o que você falou (0.6 a 5)", "num", (0.6, 5.0)),
    "voz_encerrar": ("segundos sem falar até encerrar a conversa por voz (3 a 30)", "num", (3.0, 30.0)),
    "voz_modelo_fala": ("Whisper que transcreve: base (leve) ou small (mais certo)", "opcoes",
                        {"base": "base", "leve": "base", "small": "small", "certo": "small"}),
    "voz_vocabulario": ("nomes que o reconhecimento erra, separados por vírgula", "texto", 300),
    "voz_apelidos": ("frases que me chamam, separadas por vírgula", "lista", 8),
    "voz_microfone": ("parte do nome do microfone (vazio = o padrão do Windows)", "texto", 80),
}
# o que ele fala → a chave
APELIDOS = {"junior": "modo_junior", "resumo": "resumir_avisos", "resumir": "resumir_avisos", "piadas": "comentar_tela",
            "piada": "comentar_tela", "comentarios": "comentar_tela", "tdah": "modo_tdah", "faixa": "vendado",
            "voz": "voz_fala", "falar": "voz_fala", "microfone": "voz", "ouvir": "voz", "volume": "voz_volume",
            "tom": "voz_tom", "tamanho": "tamanho", "andar": "movimento", "frequencia": "comentar_a_cada_minutos",
            "esforco": "chat_esforco", "modelo": "chat_modelo", "contorno": "borda", "ultron": "personalidade",
            "permissao": "permissao_pelo_balao", "pode nao": "permissao_pelo_balao"}
FREQUENCIAS = {"bastante": [1, 3], "muito": [1, 3], "normal": [4, 10], "de vez em quando": [15, 30], "pouco": [15, 30]}


def simples(texto):
    texto = unicodedata.normalize("NFKD", str(texto or "").lower())
    return " ".join("".join(c if c.isalnum() or c in " .-:" else " " for c in texto
                            if not unicodedata.combining(c)).split())


def achar(qual):
    q = simples(qual).replace(" ", "_")
    if q in AJUSTES:
        return q
    return APELIDOS.get(simples(qual)) or APELIDOS.get(q)


def interpretar(qual, valor, cfg, opcoes_extra=None):
    """(chave, valor pronto pro aplicar_cfg) ou ValueError com a explicação pra devolver ao chat.
    `opcoes_extra`: {chave: {o que ele diz: valor}} montado na hora (modelos, vozes instaladas)."""
    chave = achar(qual)
    if not chave:
        raise ValueError("esse eu não mudo pelo chat (ou não existe). Os que dá: " + ", ".join(AJUSTES))
    desc, tipo, extra = AJUSTES[chave]
    v = simples(valor)
    if chave == "personalidade" and simples(qual) == "ultron" and v in SIM | NAO:   # "liga o ultron"
        return chave, "ultron" if v in SIM else "claudinho"
    if tipo == "bool":
        if v not in SIM | NAO:
            raise ValueError(f"{chave} é liga/desliga: mande \"ligar\" ou \"desligar\"")
        ligar = v in SIM
        if extra == "so_ligar" and not ligar and cfg.get(chave):
            raise ValueError("isso só sai pelo painel (é privacidade): diga isso a ele")
        if extra == "so_desligar" and ligar and not cfg.get(chave):
            raise ValueError("isso só liga pelo painel (é privacidade): diga isso a ele")
        return chave, ligar
    if tipo == "opcoes":
        opcoes = (opcoes_extra or {}).get(chave) or extra or {}
        if v in opcoes:
            return chave, opcoes[v]
        achados = [val for nome, val in opcoes.items() if v and v in nome]
        if len(set(achados)) == 1:
            return chave, achados[0]
        raise ValueError(f"{chave}: escolha uma destas: " + ", ".join(dict.fromkeys(opcoes)))
    if tipo == "voz":
        vozes = (opcoes_extra or {}).get(chave) or {}
        achados = [vid for nome, vid in vozes.items() if v and v in simples(nome)]
        if len(set(achados)) == 1:
            return chave, achados[0]
        raise ValueError("vozes instaladas: " + ", ".join(vozes) + " (outras se baixam no painel)")
    if tipo == "num":
        lo, hi = extra
        try:
            n = float(str(valor).strip().replace("%", "").replace(",", "."))   # (o simples tira a vírgula)
        except ValueError:
            raise ValueError(f"{chave} é um número de {lo} a {hi}") from None
        n = max(lo, min(hi, n))
        return chave, int(n) if isinstance(lo, int) else n
    if tipo == "frequencia":
        if v in FREQUENCIAS:
            return chave, FREQUENCIAS[v]
        partes = [p for p in v.replace("a", "-").replace(" ", "").split("-") if p]
        try:
            a, b = sorted(max(1, min(120, int(p))) for p in partes[:2])
            return chave, [a, b]
        except ValueError:
            raise ValueError("frequência: bastante, normal, de vez em quando ou \"A-B\" minutos") from None
    if tipo == "lista":
        itens = [p.strip() for p in str(valor or "").split(",") if p.strip()]
        if not itens:
            raise ValueError(f"{chave}: mande os itens separados por vírgula")
        return chave, itens[:extra]
    return chave, str(valor or "").strip()[:extra]   # texto


def mostrar(valor):
    if isinstance(valor, bool):
        return "ligado" if valor else "desligado"
    if isinstance(valor, list):
        return "-".join(map(str, valor)) if all(isinstance(x, int) for x in valor) else ", ".join(map(str, valor))
    return str(valor) if valor not in ("", None) else "(vazio)"


def listar(cfg):
    return "\n".join(f"- {k}: {mostrar(cfg.get(k))} ({d})" for k, (d, _, _) in AJUSTES.items())
