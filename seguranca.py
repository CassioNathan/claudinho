"""Duas barreiras baratas (só regex, sem IA), na ideia do OpenJarvis (security/injection_scanner.py e
credential_stripper.py):

- `parece_instrucao`: texto que tenta mandar no assistente ("ignore as instruções…", "você agora é…"). Ele lê
  WhatsApp, sites, notificações e prints; um desses não pode virar fato na memória nem lembrança que vai pro chat.
- `tirar_segredos`: chave de API, token, chave privada, número de cartão. Sai do texto antes de ir pra nuvem.
"""
import re

INSTRUCAO = re.compile("|".join([
    # português
    # (só o imperativo de "você": "ele ignora as regras do jogo" é fato, não ordem)
    r"\b(ignore|desconsidere|esque[çc]a)\s+(tud[oa]\s+)?(as\s+|todas\s+as\s+|suas\s+|essas\s+)?"
    r"(instru[çc][õo]es|regras|ordens|orienta[çc][õo]es)",
    r"\b(novas?\s+instru[çc][õo]es|instru[çc][õo]es\s+do\s+sistema|prompt\s+do\s+sistema)\b",
    r"\b(voc[êe]|tu)\s+(agora\s+)?(é|e|ser[aá])\s+(agora\s+)?(um|uma|o|a)\s+(outr[oa]|nov[oa])\b",
    r"\ba\s+partir\s+de\s+agora[, ]+\s*(voc[êe]|sempre|nunca|responda|obede[çc]a)",
    r"\bfinja\s+que\s+(n[ãa]o\s+tem|est[áa]\s+sem)\s+(regras|limites|restri[çc][õo]es)",
    r"\bn[ãa]o\s+(conte|diga|avise|mostre)\s+(nada\s+)?(isso\s+)?(a[oa]|pr[oa])\s+(usu[áa]rio|dono|mestre)",
    r"\b(mande|envie|encaminhe|transfira)\s+(\w+\s+){0,4}(senhas?|chaves?|tokens?|c[óo]digos?)\b",
    # inglês
    r"\b(ignore|disregard|forget)\s+(all\s+)?(the\s+)?(previous|prior|above|your)\s+(instructions?|prompts?|rules?)",
    r"\byou\s+are\s+now\s+(a\s+)?(different|new|my)\b",
    r"\bpretend\s+(you\s+)?(have\s+)?no\s+(restrictions?|limitations?|rules?|filters?)",
    r"\b(DAN|do\s+anything\s+now)\s+(mode|prompt|jailbreak)\b",
    r"\b(system\s+prompt|developer\s+mode)\b",
    # marcações de papel que só aparecem em ataque
    r"<\|?(im_start|im_end|system|assistant)\|?>", r"```(system|assistant)\b", r"\[/?INST\]",
]), re.I)


def parece_instrucao(texto):
    """True se o texto tenta dar ordem ao assistente (não serve pra memória nem pra ir junto da conversa)."""
    return bool(texto) and bool(INSTRUCAO.search(texto))


class VigiaDeLoop:
    """O chat preso num ciclo de ferramenta (na ideia do loop_guard do OpenJarvis): a mesma chamada, igualzinha, 3
    vezes seguidas, ou duas se alternando (A, B, A, B, A, B). Só seguidas: rodar o teste de novo depois de mexer no
    código é normal. Um por pergunta."""

    def __init__(self, repeticoes=3):
        self.repeticoes, self.chamadas = repeticoes, []

    def preso(self, nome, entrada):
        """Anota a chamada; True se ela fecha um ciclo."""
        import json
        chave = nome + json.dumps(entrada, sort_keys=True, ensure_ascii=False, default=str)
        self.chamadas.append(chave)
        if self.chamadas[-self.repeticoes:] == [chave] * self.repeticoes:
            return True
        u = self.chamadas[-6:]
        return len(u) == 6 and len(set(u)) == 2 and u[0::2] == [u[0]] * 3 and u[1::2] == [u[1]] * 3


SEGREDOS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(-----END [A-Z ]*PRIVATE KEY-----|$)", re.S),
    re.compile(r"\bsk-(ant-)?[A-Za-z0-9_-]{20,}"),                 # Anthropic, OpenAI
    re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                            # AWS
    re.compile(r"\bxox[abposr]-[0-9A-Za-z-]{10,}"),                 # Slack
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),                       # Google
    re.compile(r"\bgsk_[A-Za-z0-9]{30,}"),                          # Groq
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),   # JWT
    re.compile(r"\bBearer\s+[A-Za-z0-9_\-.=]{20,}", re.I),
    # "senha: ..." escrita; `password = getpass()` em código colado continua (o valor é uma chamada)
    re.compile(r"\b(senha|password|passwd)\s*[:=]\s*[\"']?[^\s()\"',;]{6,}(?![(\w])[\"']?", re.I),
]
CARTAO = re.compile(r"\b\d(?:[ -]?\d){12,18}\b")
TROCA = "[segredo removido]"


def _luhn(digitos):
    soma = 0
    for i, d in enumerate(reversed(digitos)):
        d = int(d)
        if i % 2:
            d = d * 2 - 9 if d > 4 else d * 2
        soma += d
    return soma % 10 == 0


def tirar_segredos(texto):
    """O texto sem chaves, tokens, chaves privadas e números de cartão (os que passam no Luhn)."""
    if not texto or not isinstance(texto, str):
        return texto
    for rx in SEGREDOS:
        texto = rx.sub(TROCA, texto)

    def cartao(m):
        digitos = re.sub(r"\D", "", m.group(0))
        return TROCA if 13 <= len(digitos) <= 19 and _luhn(digitos) else m.group(0)
    return CARTAO.sub(cartao, texto)
