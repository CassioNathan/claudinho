"""Reconhecimento de fala na nuvem (opcional): manda só a fala depois da chamada pra uma API de transcrição.

O "Ei Claudinho" continua sendo detectado no próprio PC; só o que você diz depois sai daqui, e se a nuvem falhar
(sem internet, chave errada, limite) o Claudinho cai de volta no Whisper local.

Provedores (a mesma interface "/audio/transcriptions" da OpenAI; a chave é sua, guardada criptografada pelo Windows):
    groq    Whisper large-v3-turbo: o mais barato e o mais rápido (na casa de centavos por hora de áudio)
    openai  gpt-4o-mini-transcribe: um pouco mais caro
Os preços mudam: confira na página do provedor antes de usar bastante.
"""
import io
import json
import urllib.error
import urllib.request
import uuid
import wave

import numpy as np

TAXA = 16000
PROVEDORES = {
    "groq": {"nome": "Groq (Whisper large-v3-turbo, bem barato)",
             "url": "https://api.groq.com/openai/v1/audio/transcriptions",
             "modelo": "whisper-large-v3-turbo", "formato": "verbose_json"},
    "openai": {"nome": "OpenAI (gpt-4o-mini-transcribe)",
               "url": "https://api.openai.com/v1/audio/transcriptions",
               "modelo": "gpt-4o-mini-transcribe", "formato": "json"},
}


class ErroSTT(Exception):
    pass


def _wav(audio):
    """Áudio float 16 kHz mono → WAV de 16 bits na memória."""
    saida = io.BytesIO()
    with wave.open(saida, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes((np.clip(audio, -1.0, 1.0) * 32767).astype("<i2").tobytes())
    return saida.getvalue()


def _multipart(campos, arquivo):
    fronteira = uuid.uuid4().hex
    corpo = b""
    for nome, valor in campos.items():
        corpo += (f"--{fronteira}\r\nContent-Disposition: form-data; name=\"{nome}\"\r\n\r\n{valor}\r\n").encode()
    corpo += (f"--{fronteira}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"fala.wav\"\r\n"
              "Content-Type: audio/wav\r\n\r\n").encode() + arquivo + f"\r\n--{fronteira}--\r\n".encode()
    return corpo, f"multipart/form-data; boundary={fronteira}"


def transcrever(audio, provedor, chave, idioma="pt", prompt=None, timeout=10, url=None):
    """(texto, confiança). Confiança = média do avg_logprob dos trechos (0 = certeza) quando o provedor informa
    (Groq), senão 0. Levanta ErroSTT com uma mensagem em português se não deu."""
    info = PROVEDORES.get(provedor)
    if not info or not chave:
        raise ErroSTT("falta escolher o provedor ou colar a chave")
    campos = {"model": info["modelo"], "language": idioma, "temperature": "0", "response_format": info["formato"]}
    if prompt:
        campos["prompt"] = prompt
    corpo, tipo = _multipart(campos, _wav(audio))
    pedido = urllib.request.Request(url or info["url"], data=corpo, headers={
        "Authorization": f"Bearer {chave}", "Content-Type": tipo, "User-Agent": "Claudinho"})
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as r:
            dados = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detalhe = ""
        try:
            detalhe = json.loads(e.read()).get("error", {}).get("message", "")
        except Exception:
            pass
        if e.code in (401, 403):
            raise ErroSTT("a chave foi recusada pelo provedor") from e
        if e.code == 429:
            raise ErroSTT("limite de uso do provedor atingido") from e
        raise ErroSTT(f"erro {e.code} do provedor {detalhe[:120]}".strip()) from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ErroSTT(f"sem resposta do provedor ({getattr(e, 'reason', e)})") from e
    texto = (dados.get("text") or "").strip()
    trechos = dados.get("segments") or []
    if not trechos:
        return texto, 0.0
    logprob = float(np.mean([t.get("avg_logprob", 0.0) for t in trechos]))
    sem_fala = float(np.max([t.get("no_speech_prob", 0.0) for t in trechos]))
    return texto, (logprob if sem_fala < 0.6 else -5.0)


def testar(provedor, chave, url=None):
    """Manda meio segundo de silêncio só pra ver se a chave vale. Devolve (ok, mensagem)."""
    try:
        transcrever(np.zeros(TAXA // 2, dtype="float32"), provedor, chave, timeout=15, url=url)
        return True, "chave funcionando ✓"
    except ErroSTT as e:
        return False, str(e)
