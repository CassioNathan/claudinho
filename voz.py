"""Comando por voz do Claudinho: chamou pelo apelido, o chat abre e ele escuta, digitando o que você fala.

Tudo local: um detector de voz leve (Silero, que vem junto do faster-whisper) fica ouvindo o microfone, e só
quando alguém fala ele passa aquele pedacinho de áudio pra um Whisper pequeno, que vê se tem o apelido. Os
apelidos são só texto (sem treinar nada): a comparação é aproximada, então "Cloudinho" ainda vale.

    ouvindo apelido → (chamou) carrega o Whisper melhor, abre o chat e faz "tuk-tuk" → você fala, o texto vai
    aparecendo → ficou em silêncio: "tuk" mais grave e o texto é enviado.

Quem usa só entrega os callbacks (que rodam na thread da voz: o Claudinho joga tudo numa fila pra thread da tela).
"""
import collections
import difflib
import io
import math
import queue
import re
import threading
import time
import unicodedata
import wave
import zlib
from pathlib import Path

import stt

import numpy as np

TAXA = 16000
BLOCO = 2048                    # 128 ms por bloco do microfone
SEG_BLOCO = BLOCO / TAXA
FRASES_CANCELAR = {"cancela", "cancelar", "cancelado", "esquece", "esqueca", "deixa pra la", "deixa quieto",
                   "tchau", "encerrar", "encerra", "pode encerrar", "chega", "fim"}
# frases que terminam nisso quase sempre continuam: espera mais antes de mandar
PALAVRAS_ABERTAS = {"e", "mas", "que", "entao", "tipo", "ne", "ai", "ou", "porque", "pra", "para", "com", "de", "do",
                    "da", "dos", "das", "no", "na", "em", "a", "o", "um", "uma", "se", "quando", "como", "tambem",
                    "porem", "so", "ate", "depois", "antes", "sobre", "entre", "pelo", "pela", "por"}
EXTRA_FRASE_ABERTA = 1.2        # segundos a mais de silêncio quando a frase parece incompleta


def frase_aberta(texto):
    """A frase parece incompleta (termina em "e", "mas", "tipo", vírgula, reticências…)?"""
    texto = texto.strip()
    if not texto or texto.endswith(("?", "!")):
        return False
    if texto.endswith((",", "…", "...", "-", ":", ";")):
        return True
    palavras = normalizar(texto)
    return bool(palavras) and palavras[-1] in PALAVRAS_ABERTAS


INCERTO = object()               # o Whisper não entendeu: pede pra repetir em vez de mandar
LIMITE_CONFIANCA = -1.0         # log-prob médio abaixo disso = chute
PICO_MINIMO = 0.04                # fala com pico abaixo disso é ruído de fundo: nem vai pro reconhecimento
CONFIANCA_CHAMADA = -0.6           # chamada só vale se o Whisper estiver razoavelmente seguro
NIVEL_MINIMO = 0.1                # a voz precisa ter ≥ 10% (−20 dB) do volume da chamada: só barra TV e gente longe
GANHO_ALVO = 0.08               # volume (RMS) que o ganho automático procura na fala
GANHO_MAX = 25.0                # até quantas vezes ele aumenta o microfone
LIMIAR_VOZ = 0.4                # abaixo do 0,5 padrão: pega voz baixa ou longe do microfone
ESPERA_INICIAL = 8.0            # chamou e não falou nada: desiste depois disso
MAX_DICA = 180                  # caracteres de vocabulário na dica do Whisper (o limite dele é ~224 tokens)
RUIDO_CLASSICO = {"obrigado", "obrigada", "tchau", "tchau tchau", "muito obrigado", "obrigado por assistir"}
ALUCINACOES = ("legendas pela comunidade", "amara.org", "obrigado por assistir", "inscreva-se")


def normalizar(texto):
    """minúsculas, sem acento nem pontuação: o que o Whisper escreve e o que você digitou ficam comparáveis"""
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", texto).split()


def achar_apelido(texto, apelidos, minimo=0.78, inicio_max=None):
    """O texto chama algum apelido? Devolve (achou, o_que_veio_depois). Compara palavra a palavra (ou grupos
    de palavras, se o apelido tiver mais de uma), aceitando erro de escuta."""
    palavras = texto.split()
    norm = [(" ".join(normalizar(p)) or "") for p in palavras]
    for apelido in apelidos:
        alvo = normalizar(apelido)
        if not alvo:
            continue
        n = len(alvo)
        corte = max(minimo, 0.85 if sum(map(len, alvo)) <= 4 else minimo)
        for i in range(len(norm) - n + 1):
            if inicio_max is not None and i > inicio_max:   # a chamada vem no começo da fala, não no meio de um comentário
                break
            janela = norm[i:i + n]
            if n == 1:
                bateu = bool(janela[0]) and difflib.SequenceMatcher(None, janela[0], alvo[0]).ratio() >= corte
            else:   # frase de chamada: cada palavra tem que bater com a sua ("pro" não vale por "oi"); o nome, mais exigente
                bateu = all(
                    p and difflib.SequenceMatcher(None, p, a).ratio() >= (0.82 if j == n - 1 else 0.66 if len(a) <= 3 else minimo)
                    for j, (p, a) in enumerate(zip(janela, alvo)))
            if bateu:
                resto = " ".join(palavras[i + n:]).strip(" ,.;:!?-–…")
                return True, resto
    return False, ""


def _tom(frequencias, ms=80, volume=0.09):
    """WAV curtinho na memória: uma notinha suave por frequência (entra e sai devagar, sem clique nem estridência)."""
    pedacos = []
    for f in frequencias:
        n = int(TAXA * ms / 1000)
        t = np.arange(n) / TAXA
        envelope = np.sin(np.pi * np.arange(n) / n) ** 2           # sobe e desce macio (cosseno levantado)
        onda = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)) / 1.25 * envelope * volume
        pedacos += [onda, np.zeros(int(TAXA * 0.03))]
    dados = (np.concatenate(pedacos) * 32767).astype("<i2").tobytes()
    saida = io.BytesIO()
    with wave.open(saida, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes(dados)
    return saida.getvalue()


SONS = {
    "pronto": _tom([523, 659]),         # dó-mi subindo: pode falar
    "enviado": _tom([659, 523]),        # mi-dó descendo: parei de ouvir, vou responder
    "cancelado": _tom([392]),
    "fim": _tom([523, 440, 349]),       # conversa encerrada: voltou a esperar só o apelido
    "nao_entendi": _tom([440, 440]),
}


def microfones():
    """Nomes dos microfones (sem repetir o mesmo em cada driver) pro painel escolher."""
    try:
        import sounddevice as sd
        nomes = []
        for d in sd.query_devices():
            nome = d["name"]
            if d["max_input_channels"] > 0 and "mapeador" not in nome.lower() and "driver de" not in nome.lower()                     and nome not in nomes:
                nomes.append(nome)
        return nomes
    except Exception:
        return []


def limpar_ruido(audio, taxa=TAXA):
    """Filtro de ruído por subtração espectral: o ruído de fundo (chiado, ventilador, ar-condicionado) é estimado
    nos trechos mais quietos do próprio áudio e abatido de cada pedacinho do espectro, com um piso (a voz não
    fica "robótica"). Corta também o grave abaixo de ~70 Hz (rumble). Áudio já limpo sai quase igual."""
    n_fft, hop = 512, 128
    if len(audio) < n_fft * 4:
        return audio
    janela = np.hanning(n_fft).astype("float32")
    x = np.pad(audio.astype("float32"), (n_fft, n_fft))
    quadros = np.lib.stride_tricks.sliding_window_view(x, n_fft)[::hop] * janela
    esp = np.fft.rfft(quadros, axis=1)
    mag = np.abs(esp)
    energia = (mag ** 2).sum(axis=1)
    k = max(3, int(len(energia) * 0.15))
    ruido = np.sqrt(np.mean(mag[np.argsort(energia)[:k]] ** 2, axis=0))      # perfil do ruído por frequência
    mascara = np.clip(1.0 - 1.6 * ruido[None, :] / np.maximum(mag, 1e-9), 0.12, 1.0)
    mascara = (mascara + np.roll(mascara, 1, axis=0) + np.roll(mascara, -1, axis=0)) / 3   # suaviza no tempo
    mascara[:, np.fft.rfftfreq(n_fft, 1 / taxa) < 70] = 0.0
    saida_q = np.fft.irfft(esp * mascara, n=n_fft, axis=1) * janela
    saida = np.zeros(len(x), dtype="float32")
    peso = np.zeros(len(x), dtype="float32")
    for idx, q in enumerate(saida_q):
        a = idx * hop
        saida[a:a + n_fft] += q
        peso[a:a + n_fft] += janela ** 2
    saida = saida / np.maximum(peso, 1e-6)
    return saida[n_fft:-n_fft]


def preparar(audio, limpar=True):
    """Prepara pro Whisper: filtro de ruído e, microfone baixo ou longe, tira o DC e sobe o volume até o pico ficar
    em ~0,6 (no máximo 40x). Áudio quase mudo (só ruído de fundo) fica como está pra não virar chiado alto."""
    if limpar:
        audio = limpar_ruido(audio)
    audio = audio - float(np.mean(audio))
    pico = float(np.percentile(np.abs(audio), 99.5)) if len(audio) else 0.0
    if pico < 0.004:
        return audio.astype("float32")
    return np.clip(audio * min(0.6 / pico, 40.0), -1.0, 1.0).astype("float32")


def repetitivo(texto):
    """O Whisper com áudio ruim cai em "e o que é o que é o que é…": isso comprime demais."""
    if len(texto) < 25:
        return False
    cru = texto.encode("utf-8")
    return len(cru) / len(zlib.compress(cru)) > 2.4


def registrar(linha):
    """Uma linha por transcrição em ~/.claudinho/voz.log (pra ajustar a escuta com dados de verdade)."""
    try:
        pasta = Path.home() / ".claudinho"
        arq = pasta / "voz.log"
        if arq.exists() and arq.stat().st_size > 200_000:
            arq.replace(pasta / "voz.log.1")
        with open(arq, "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S ") + linha + "\n")
    except Exception:
        pass


def tocar(nome):
    """O winsound não toca da memória em modo assíncrono (dá RuntimeError): toca direto, numa thread."""
    def _tocar():
        try:
            import winsound
            winsound.PlaySound(SONS[nome], winsound.SND_MEMORY)
        except Exception:
            pass
    threading.Thread(target=_tocar, daemon=True).start()


class Voz:
    def __init__(self, config, ao_acordar, ao_texto, ao_enviar, ao_cancelar, pausado=lambda: False, ao_erro=print,
                 ao_estado=lambda e: None, conversa_viva=lambda: True, fala=None, chave_stt=lambda: None, saudacao=lambda: None,
                 vocabulario=lambda: ""):
        """config(): dict com voz_apelidos, voz_silencio, voz_microfone, voz_modelo_apelido, voz_modelo_fala,
        voz_sons (relido a cada uso: mudar no painel vale na hora)."""
        self.config = config
        self.ao_acordar, self.ao_texto, self.ao_enviar = ao_acordar, ao_texto, ao_enviar
        self.ao_cancelar, self.pausado, self.ao_erro = ao_cancelar, pausado, ao_erro
        self.ao_estado, self.conversa_viva = ao_estado, conversa_viva
        self.fala = fala             # fala.Fala: a voz do Claudinho (None = só texto)
        self.saudacao = saudacao     # () -> cumprimento curto que ele fala quando a conversa por voz começa (ou None)
        # () -> nomes que você costuma falar (programas, projetos, artistas): vão de dica pro Whisper escrever certo
        self.vocabulario = vocabulario
        self.chave_stt = chave_stt   # a chave do provedor de reconhecimento na nuvem (guardada criptografada)
        self.nuvem_erro = None       # por que a última tentativa na nuvem caiu pro local (None = deu certo)
        self.ultimo_motor = "local"  # quem fez a última transcrição: "nuvem" ou "local" (vai pro voz.log)
        self.resposta = threading.Event()   # o Claudinho avisa (resposta_chegou) quando terminou de responder
        self.fila = queue.Queue(maxsize=200)
        # o que o microfone está pegando, pro Claudinho desenhar a faixa de áudio: ~30 valores por segundo, de 0 a 1
        self.niveis = collections.deque([0.0] * 48, maxlen=48)
        self.em_voz = False         # o detector acha que é fala (a faixa fica laranja)
        self.nivel_chamada = 0.0     # volume da sua chamada ("Ei Claudinho"): referência de quem está falando com ele
        self.ganho, self.piso = 1.0, 1e-3    # ganho automático do microfone e o nível do ruído de fundo
        self.rodando = False
        self.fio = None
        self.modelos, self.trava_modelos = {}, threading.Lock()
        self.trava_transcricao = threading.Lock()
        self.vad = None
        self.estado = "parado"      # parado | ouvindo_apelido | acordando | ouvindo_fala | enviando
        self.ultimo_uso_fala = 0.0
        self.ditando = False                  # botão do microfone do chat: grava e entrega o texto (sem chamada, sem enviar)
        self.parar_ditado = threading.Event()  # o botão de novo: para de gravar e transcreve o que tem

    # ---------- ligar / desligar ----------
    def ligar(self):
        if self.fio and self.fio.is_alive():
            return
        self.rodando = True
        self.fio = threading.Thread(target=self._rodar, daemon=True)
        self.fio.start()

    def desligar(self):
        self.rodando = False
        self.estado = "parado"

    def reiniciar(self):
        """Mudou o microfone: fecha e abre de novo."""
        if self.rodando:
            self.desligar()
            if self.fio:
                self.fio.join(timeout=3)
            self.ligar()

    # ---------- modelos (carrega só quando precisa; o do apelido fica, o da fala sai depois de um tempo) ----------
    def _whisper(self, nome, gpu=False):
        from faster_whisper import WhisperModel
        with self.trava_modelos:
            chave = (nome, gpu)
            if chave not in self.modelos:
                try:
                    self.modelos[chave] = WhisperModel(nome, device="cuda" if gpu else "cpu",
                                                       compute_type="float16" if gpu else "int8")
                except Exception:
                    if not gpu:
                        raise
                    chave = (nome, False)  # sem CUDA: cai pra CPU
                    if chave not in self.modelos:
                        self.modelos[chave] = WhisperModel(nome, device="cpu", compute_type="int8")
            return self.modelos[chave]

    def _descarregar_fala_parada(self):
        cfg = self.config()
        with self.trava_modelos:
            if self.ultimo_uso_fala and time.time() - self.ultimo_uso_fala > 300:
                for chave in [k for k in self.modelos if k[0] == cfg["voz_modelo_fala"]
                              and cfg["voz_modelo_fala"] != cfg["voz_modelo_apelido"]]:
                    del self.modelos[chave]
                self.ultimo_uso_fala = 0.0

    def usar_nuvem(self):
        return self.config().get("voz_reconhecimento") in stt.PROVEDORES and bool(self.chave_stt())

    def _transcrever_nuvem(self, audio):
        """Fala já pronta (depois da chamada) vai pra nuvem; None = não deu, usa o Whisper local."""
        try:
            texto, conf = stt.transcrever(preparar(audio, False), self.config()["voz_reconhecimento"], self.chave_stt())
            self.nuvem_erro = None
            self.ultimo_motor = "nuvem"
            return texto, conf
        except stt.ErroSTT as e:
            if str(e) != self.nuvem_erro:
                self.ao_erro(f"reconhecimento na nuvem falhou ({e}); usando o Whisper local")
            self.nuvem_erro = str(e)
            return None

    def transcrever_detalhado(self, audio, modelo, prompt=None, beam=3):
        """(texto, confiança): confiança é a média do log-prob dos trechos (0 = certeza; < -1 = chute) e vira -5 se
        o Whisper achou que não era fala. Texto vazio quando parece alucinação (repetição, legenda inventada)."""
        if beam >= 3 and self.usar_nuvem():   # beam 1 = detectar a chamada e texto parcial: sempre local
            r = self._transcrever_nuvem(audio)
            if r is not None:
                texto, conf = r
                if not texto or any(a in texto.lower() for a in ALUCINACOES) or repetitivo(texto):
                    return "", -9.0
                if " ".join(normalizar(texto)) in RUIDO_CLASSICO and len(audio) / TAXA < 4 and conf < -0.5:
                    return "", -9.0
                return texto, conf
        self.ultimo_motor = "local"
        audio = preparar(audio, bool(self.config().get("voz_limpar", True)))
        with self.trava_transcricao:
            segmentos, _ = self._whisper(modelo).transcribe(
                audio, language="pt", beam_size=beam, condition_on_previous_text=False, vad_filter=False,
                initial_prompt=prompt, temperature=[0.0, 0.2, 0.4], compression_ratio_threshold=2.2,
                log_prob_threshold=-1.2, no_speech_threshold=0.6, repetition_penalty=1.1)
            segmentos = list(segmentos)
        texto = " ".join(s.text.strip() for s in segmentos).strip()
        if not segmentos or any(a in texto.lower() for a in ALUCINACOES) or repetitivo(texto):
            return "", -9.0
        if prompt:   # vazou a dica: o texto é (quase) a dica inteira, não uma chamada curta como "Ei, Claudinho!"
            t, p = " ".join(normalizar(texto)), " ".join(normalizar(prompt))
            if len(p.split()) >= 4 and t in p and len(t.split()) >= 0.6 * len(p.split()):
                return "", -9.0
        logprob = float(np.mean([s.avg_logprob for s in segmentos]))
        sem_fala = float(np.max([s.no_speech_prob for s in segmentos]))
        if " ".join(normalizar(texto)) in RUIDO_CLASSICO and len(audio) / TAXA < 4 and logprob < -0.5:
            return "", -9.0   # o Whisper "ouve" um "Obrigado." no meio do ruído
        return texto, (logprob if sem_fala < 0.6 else -5.0)

    def _dica_vocabulario(self):
        """A dica do texto final: "Spotify, IntelliJ, Legião Urbana." (curta: dica longa o Whisper "ouve" no ruído)."""
        try:
            termos = [t.strip() for t in (self.vocabulario() or "").split(",") if t.strip()]
        except Exception:
            return None
        dica = ""
        for t in dict.fromkeys(termos):
            if len(dica) + len(t) + 2 > MAX_DICA:
                break
            dica += (", " if dica else "") + t
        return dica + "." if dica else None

    def transcrever(self, audio, modelo, prompt=None):
        return self.transcrever_detalhado(audio, modelo, prompt)[0]

    # ---------- detector de voz ----------
    def _prob_voz(self, janela):
        """Probabilidade de voz nos últimos blocos (a janela é o último ~1 s de áudio)."""
        if self.vad is None:
            from faster_whisper.vad import SileroVADModel, get_assets_path
            import os
            self.vad = SileroVADModel(os.path.join(get_assets_path(), "silero_vad_v6.onnx"))
        n = (len(janela) // 512) * 512
        if n < 512:
            return 0.0
        janela = janela[-n:]
        pico = float(np.max(np.abs(janela)))
        if 0.004 < pico < 0.3:   # voz baixa ou longe do microfone: sobe o volume só pra detectar
            janela = janela * (0.3 / pico)
        p = self.vad(np.ascontiguousarray(janela), 512)
        return float(np.max(p[-4:]))  # os últimos 128 ms

    # ---------- microfone ----------
    def _dispositivo(self):
        import sounddevice as sd
        nome = (self.config().get("voz_microfone") or "").strip().lower()
        if not nome:
            return None
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0 and nome in d["name"].lower():
                return i
        return None

    def _rodar(self):
        import sounddevice as sd
        try:
            self.estado = "ouvindo_apelido"
            self._whisper(self.config()["voz_modelo_apelido"])  # já carrega o do apelido, pra primeira chamada ser rápida
            fluxo = sd.InputStream(samplerate=TAXA, channels=1, dtype="float32", blocksize=BLOCO,
                                   device=self._dispositivo(), callback=self._ao_receber)
        except Exception as e:
            self.estado = "parado"
            self.rodando = False
            self.ao_erro(f"não consegui abrir o microfone ou o Whisper ({e})")
            return
        with fluxo:
            self._laco()
        self.estado = "parado"

    def _ganho_automatico(self, bloco):
        """Microfone longe ou baixo: sobe o ganho devagar (até 25x) enquanto tem voz acima do ruído de fundo, e
        baixa rápido se a voz ficar alta. No silêncio ele não sobe, pra não amplificar o chiado."""
        rms = float(np.sqrt(np.mean(bloco ** 2))) + 1e-9
        self.piso = rms if rms < self.piso else self.piso + (rms - self.piso) * 0.003   # ruído: desce rápido, sobe devagar
        self.piso = max(self.piso, 1e-5)
        if rms > self.piso * 2.2 and rms > 0.0012:       # tem sinal de verdade acima do ruído
            alvo = max(1.0, min(GANHO_MAX, GANHO_ALVO / rms))
            self.ganho += (alvo - self.ganho) * (0.05 if alvo > self.ganho else 0.3)
        else:
            self.ganho += (1.0 - self.ganho) * 0.0015    # aos poucos esquece o ganho no silêncio longo
        return np.clip(bloco * self.ganho, -1.0, 1.0)

    def _ao_receber(self, dados, frames, tempo, status):
        bloco = dados[:, 0]
        # o ganho automático só vale pra faixa de áudio na tela: pro Whisper o sinal vai cru (nada de estourar) e
        # cada fala é normalizada de uma vez em preparar(); antes ele ia amplificado e batia em 1.0 (clipping)
        visivel = self._ganho_automatico(bloco) if self.config().get("voz_limpar", True) else bloco
        for pedaco in np.array_split(visivel, 4):   # 4 valores por bloco de 128 ms: a faixa anda macia
            rms = float(np.sqrt(np.mean(pedaco ** 2))) if len(pedaco) else 0.0
            db = 20 * math.log10(rms + 1e-6)
            self.niveis.append(min(1.0, max(0.0, (db + 60) / 30)))   # -60 dB (silêncio) a -30 dB (voz normal)
        try:
            self.fila.put_nowait(bloco.copy())
        except queue.Full:
            pass

    def _nivel_ok(self, bloco):
        """Voz bem mais baixa que a da chamada (TV, outra pessoa longe) não conta como você falando."""
        ref = self.nivel_chamada
        if ref <= 0 or not self.config().get("voz_travar_nivel", True):
            return True
        return float(np.percentile(np.abs(bloco), 90)) >= ref * NIVEL_MINIMO

    def _limpar_fila(self):
        while True:
            try:
                self.fila.get_nowait()
            except queue.Empty:
                return

    def _laco(self):
        janela = np.zeros(0, dtype="float32")
        pre = []          # ~0,5 s antes de começar a falar
        segmento = []     # o que você está falando (esperando o apelido)
        silencio = 0
        ultima_checagem = 0.0
        pausado = False
        estava_ditando = False
        while self.rodando:
            if self.ditando:   # o ditado usa o microfone sozinho: a escuta da chamada espera e recomeça limpa
                estava_ditando = True
                time.sleep(0.05)
                continue
            if estava_ditando:
                estava_ditando = False
                janela, pre, segmento, silencio = janela[:0], [], [], 0
            try:
                bloco = self.fila.get(timeout=0.5)
            except queue.Empty:
                continue
            if time.time() - ultima_checagem > 1.0:
                ultima_checagem = time.time()
                pausado = bool(self.pausado())
                self._descarregar_fala_parada()
            if pausado:
                janela, pre, segmento, silencio = janela[:0], [], [], 0
                continue
            janela = np.concatenate([janela, bloco])[-TAXA:]
            tem_voz = self.em_voz = self._prob_voz(janela) > LIMIAR_VOZ
            if tem_voz:
                if not segmento:
                    segmento = list(pre)
                segmento.append(bloco)
                silencio = 0
            elif segmento:
                segmento.append(bloco)
                silencio += 1
            else:
                pre = (pre + [bloco])[-10:]
            curto = len(segmento) < 2.2 / SEG_BLOCO   # "Claudinho" sozinho é curto: não precisa esperar tanto
            fim = bool(segmento) and (silencio >= (2 if curto else 4) or len(segmento) > 8 / SEG_BLOCO)
            if fim:
                audio = np.concatenate(segmento)
                segmento, silencio, pre = [], 0, []
                if len(audio) > 0.25 * TAXA:
                    self._checar_apelido(audio)
                janela = janela[:0]

    # ---------- ditado (botão do microfone do chat) ----------
    def ditar(self, ao_estado, ao_texto, ao_erro=None):
        """Grava até você parar de falar (ou até `parar_ditado`) e entrega o texto por `ao_texto(texto)`; texto vazio =
        não ouviu nada. `ao_estado("ouvindo" | "transcrevendo" | "fim")` acompanha. Roda numa thread; não envia nada."""
        if self.ditando:
            return
        self.ditando = True
        self.parar_ditado.clear()
        threading.Thread(target=self._ditar, args=(ao_estado, ao_texto, ao_erro or self.ao_erro), daemon=True).start()

    def _ditar(self, ao_estado, ao_texto, ao_erro):
        import sounddevice as sd
        cfg = self.config()
        fluxo = None
        texto, audio = "", None
        try:
            ao_estado("ouvindo")
            if not (self.fio and self.fio.is_alive() and self.rodando):   # sem a escuta ligada: abre o microfone só pra isso
                fluxo = sd.InputStream(samplerate=TAXA, channels=1, dtype="float32", blocksize=BLOCO,
                                       device=self._dispositivo(), callback=self._ao_receber)
                fluxo.start()
            self._limpar_fila()
            if not self.usar_nuvem():   # o modelo local carrega enquanto você fala (a primeira vez demora um pouco)
                threading.Thread(target=lambda: self._whisper(cfg["voz_modelo_fala"]), daemon=True).start()
            janela = np.zeros(0, dtype="float32")
            pre, buffer, falou, silencio = [], [], False, 0
            inicio = time.time()
            limite_silencio = max(1.0, float(cfg.get("voz_silencio", 2.5))) / SEG_BLOCO
            while not self.parar_ditado.is_set() and time.time() - inicio < 120:
                try:
                    bloco = self.fila.get(timeout=0.3)
                except queue.Empty:
                    continue
                janela = np.concatenate([janela, bloco])[-TAXA:]
                tem_voz = self.em_voz = self._prob_voz(janela) > LIMIAR_VOZ
                if tem_voz:
                    if not falou:
                        buffer, falou = list(pre), True
                    buffer.append(bloco)
                    silencio = 0
                elif falou:
                    buffer.append(bloco)
                    silencio += 1
                    if silencio >= limite_silencio:
                        break
                else:
                    pre = (pre + [bloco])[-4:]
                    if time.time() - inicio > 15:   # 15 s sem ninguém falar: desiste
                        break
            if falou:
                audio = np.concatenate(buffer)
            elif self.parar_ditado.is_set() and pre:   # parou à mão sem a voz passar do detector: usa o que pegou
                audio = np.concatenate(pre)
        except Exception as e:
            ao_erro(f"o ditado não funcionou ({e})")
        finally:
            if fluxo is not None:
                try:
                    fluxo.stop()
                    fluxo.close()
                except Exception:
                    pass
            self.em_voz = False
        try:
            if audio is not None and len(audio) > 0.3 * TAXA:
                ao_estado("transcrevendo")
                texto, _ = self.transcrever_detalhado(audio, cfg["voz_modelo_fala"], beam=3)
                registrar(f"ditado motor={self.ultimo_motor} | {texto}")
        except Exception as e:
            ao_erro(f"o ditado não funcionou ({e})")
        finally:
            self.ditando = False   # só agora a escuta da chamada volta
            ao_estado("fim")
        ao_texto(texto.strip())

    # ---------- apelido ----------
    def _checar_apelido(self, audio):
        cfg = self.config()
        apelidos = [a for a in cfg["voz_apelidos"] if a.strip()]
        if not apelidos:
            return
        pico = float(np.max(np.abs(audio))) if len(audio) else 0.0
        if pico < PICO_MINIMO:   # baixo demais pra ser você falando com ele: ruído de fundo, nem gasta reconhecimento
            return
        try:
            # dica só com o nome (a última palavra das frases): a lista inteira de frases o Whisper "ouvia" no ruído
            nome = max({a.split()[-1] for a in apelidos}, key=lambda n: sum(a.split()[-1] == n for a in apelidos))
            texto, conf = self.transcrever_detalhado(audio, cfg["voz_modelo_apelido"], prompt=nome + ".", beam=1)
        except Exception as e:
            self.ao_erro(f"o Whisper falhou ({e})")
            return
        achou, resto = achar_apelido(texto, apelidos, inicio_max=3)
        palavras = normalizar(texto)
        if achou and sum(1 for a in apelidos if all(w in palavras for w in normalizar(a))) >= 2 and pico < 0.35:
            # duas frases de chamada diferentes de uma vez, baixinho: é o Whisper repetindo a dica, não você
            registrar(f"chamada IGNORADA (eco da dica, pico={pico:.3f}) | {texto}")
            return
        if achou and conf < CONFIANCA_CHAMADA:
            # com a dica das frases na mão o Whisper "ouve" um "Oi Claudinho" no meio do ruído: sem confiança, não vale
            registrar(f"chamada IGNORADA (confiança baixa {conf:.2f}, pico={pico:.3f}) | {texto}")
            return
        if achou:
            registrar(f"chamada ACORDOU conf={conf:.2f} pico={pico:.3f} | {texto}")
            self.nivel_chamada = float(np.percentile(np.abs(audio), 90))
            self._conversar(resto)
        elif "claud" in " ".join(normalizar(texto)):   # só registra o que parecia a chamada (nada da conversa da sala)
            registrar(f"chamada quase, não acordou conf={conf:.2f} pico={pico:.3f} | {texto}")

    # ---------- a conversa (só nasce de uma chamada por voz; o chat digitado não passa por aqui) ----------
    def resposta_chegou(self):
        self.resposta.set()

    def _sinal(self, nome):
        if self.config().get("voz_sons", True):
            tocar(nome)

    def _conversar(self, inicio):
        """Chamou: abre o chat (preparando…), carrega o Whisper melhor e faz 'tuk-tuk'. Daí em diante é uma conversa:
        você fala, ele manda, responde, faz 'tuk-tuk' e espera a próxima, sem precisar chamar de novo. Dois contadores:
        voz_silencio (calou: envia) e voz_encerrar (ficou sem falar depois da resposta: encerra a conversa)."""
        cfg = self.config()
        self.estado = "acordando"
        self.ao_estado("chamado")   # o mascote já reage (sem abrir o chat) enquanto carrega o que precisa
        try:
            self._whisper(cfg["voz_modelo_fala"])  # a "carregadinha" de 1-2 s: o balão só abre depois dela
            self.ultimo_uso_fala = time.time()
        except Exception as e:
            self.ao_erro(f"não consegui carregar o Whisper ({e})")
            self.estado = "ouvindo_apelido"
            self.ao_estado("fim")
            return
        if not self.ao_acordar():  # o Claudinho não pode agora (pensando, vendo outra coisa)
            self.estado = "ouvindo_apelido"
            self.ao_estado("fim")
            return
        espera, primeira = ESPERA_INICIAL, True
        falou_resposta, uma_so = False, False
        # conversa por voz começando (e você não já veio com a pergunta): ele cumprimenta, pra você saber que abriu
        oi = self.saudacao() if (not inicio and self.fala and cfg.get("voz_fala", True)
                                 and cfg.get("voz_saudacao", True)) else None
        if oi:
            self.fala.falar(oi)
            self._esperar_fala()   # microfone fechado enquanto ele fala; o fim da fala já é o sinal
            falou_resposta = True
        while self.rodando and self.conversa_viva():
            if not (primeira and inicio):  # "Claudinho, que horas são?" numa frase só: já tem pergunta
                self.ao_estado("ouvindo")
                if not falou_resposta:  # depois da voz dele não precisa do sinal: o fim da fala já avisa
                    self._sinal("pronto")
                time.sleep(0.15 if falou_resposta else 0.45)  # o próprio tuk-tuk não pode entrar no que ele escuta
                self._limpar_fila()
                texto = self._ouvir_turno(espera)
            else:
                texto = inicio
                self.ao_texto(texto)
            if texto is INCERTO:    # não entendi: pede pra repetir sem gastar o turno
                self.ao_estado("nao_entendi")
                self._sinal("nao_entendi")
                time.sleep(0.5)
                continue
            if texto is None:       # silêncio ou "cancela": fim
                break
            self.resposta.clear()
            self.ao_estado("enviando")
            self.ao_enviar(texto)
            self._limpar_fila()
            self.estado = "esperando_resposta"
            if not self.resposta.wait(180):
                break
            primeira = False
            espera = float(self.config().get("voz_encerrar", 8))   # agora vale o contador de encerrar a conversa
            # a resposta pode estar sendo falada (em fluxo, desde a primeira frase): espera acabar, ou você interromper
            falou_resposta = bool(self.fala and self.config().get("voz_fala", True) and self.fala.ocupada)
            if falou_resposta:
                self._esperar_fala()
            if not self.config().get("voz_continua", False):   # uma pergunta por chamada: respondeu, acabou
                uma_so = True
                break
        self._encerrar(primeira, som=not uma_so)

    def _esperar_fala(self):
        """Enquanto ele fala o microfone não vai pro Whisper (senão ele se ouve): o que chega é jogado fora."""
        self.ao_estado("falando")
        self.estado = "falando"
        self._limpar_fila()
        while self.rodando and self.fala.ocupada:
            if not self.conversa_viva():     # fechou o chat no meio: para de falar
                self.fala.parar()
                return
            try:
                self.fila.get(timeout=0.2)
            except queue.Empty:
                continue
        self._limpar_fila()

    def _encerrar(self, sem_resposta, som=True):
        """Fim da conversa por voz: volta a escutar só o apelido."""
        if self.fala:
            self.fala.parar()
        if som:
            self._sinal("cancelado" if sem_resposta else "fim")
        self.ao_estado("fim")
        if sem_resposta:        # desistiu antes de mandar algo: o chat aberto à toa fecha
            self.ao_cancelar()
        self._limpar_fila()
        self.estado = "ouvindo_apelido"

    def _ouvir_turno(self, espera):
        """Escuta uma fala. Devolve o texto, INCERTO (não entendi) ou None (não falou nada dentro de `espera` s, ou
        mandou cancelar).

        O texto que aparece no campo vem do mesmo Whisper que vai mandar a mensagem, numa thread à parte: a cada
        ~1,5 s falando (rápido) e assim que você faz uma pausa (capricho, com o resultado já valendo pro envio se
        você não voltar a falar). Quando o silêncio chega no limite, o texto quase sempre já está pronto."""
        self.estado = "ouvindo_fala"
        cfg = self.config()
        modelo = cfg["voz_modelo_fala"]
        buffer, falou, silencio, desde = [], False, 0, time.time()
        janela = np.zeros(0, dtype="float32")
        pre = []     # ~0,8 s antes de detectar a fala: sem isso a primeira palavra chega cortada
        ultimo_voz = 0                      # índice do último bloco com voz
        feito_ate = 0                       # até que bloco já mandei transcrever
        pico_turno = 0.0                    # o pico mais alto de um bloco COM voz: ruído de fundo não passa do piso
        tr = {"rodando": False, "ativo": True, "resultado": None, "aberta": False}   # a thread do texto parcial

        def transcrever_em_paralelo(audio, n, beam):
            try:
                texto, conf = self.transcrever_detalhado(audio, modelo, beam=beam)
                if tr["ativo"]:
                    if texto and conf >= LIMITE_CONFIANCA:
                        self.ao_texto(texto)
                    tr["resultado"] = (n, texto, conf)
                    tr["aberta"] = frase_aberta(texto)
            except Exception:
                pass
            finally:
                tr["rodando"] = False

        def disparar(beam):
            nonlocal feito_ate
            tr["rodando"], feito_ate = True, len(buffer)
            threading.Thread(target=transcrever_em_paralelo, args=(np.concatenate(buffer), len(buffer), beam),
                             daemon=True).start()

        while self.rodando and self.conversa_viva():
            try:
                bloco = self.fila.get(timeout=0.5)
            except queue.Empty:
                bloco = None
            cfg = self.config()
            decorrido = time.time() - desde
            if bloco is None:
                if not falou and decorrido > espera:
                    tr["ativo"] = False
                    return None
                continue
            janela = np.concatenate([janela, bloco])[-TAXA:]
            tem_voz = self.em_voz = self._prob_voz(janela) > LIMIAR_VOZ and self._nivel_ok(bloco)
            if tem_voz:
                falou, silencio = True, 0
            elif falou:
                silencio += 1
            if falou:
                buffer.append(bloco)
            else:
                pre = (pre + [bloco])[-10:]
            if tem_voz and len(buffer) == 1:
                buffer = pre + buffer
            if tem_voz:
                ultimo_voz = len(buffer)
                pico_turno = max(pico_turno, float(np.max(np.abs(bloco))))
            if not falou and decorrido > espera:       # contador de encerrar (ou de desistir da chamada)
                tr["ativo"] = False
                return None
            if falou and not tr["rodando"] and pico_turno >= PICO_MINIMO:
                if tem_voz and len(buffer) - feito_ate >= 12 and not self.usar_nuvem():   # falando: texto aparecendo
                    disparar(beam=1)
                elif not tem_voz and silencio >= 5 and feito_ate < ultimo_voz:    # pausou: já vai o caprichado
                    disparar(beam=3)
            # contador de enviar (a frase parecendo incompleta, tipo "…e", ganha um tempinho extra)
            limite = float(cfg.get("voz_silencio", 2.5)) + (EXTRA_FRASE_ABERTA if tr["aberta"] else 0.0)
            if falou and silencio * SEG_BLOCO >= limite:
                break
            if decorrido > 90:
                break
        if not falou or not buffer:
            tr["ativo"] = False
            return None
        if pico_turno < PICO_MINIMO:   # só ruído de fundo (volume lá embaixo): não tem o que transcrever
            tr["ativo"] = False
            registrar(f"fala ignorada: baixa demais (pico={pico_turno:.3f})")
            return None
        self.estado = "enviando"
        self.ao_estado("enviando")
        self._sinal("enviado")  # parou de ouvir: vai responder
        fim = time.time() + 8
        while tr["rodando"] and time.time() < fim:   # a transcrição da pausa quase sempre já terminou
            time.sleep(0.05)
        tr["ativo"] = False
        audio = np.concatenate(buffer)
        r = tr["resultado"]
        if r and r[0] >= ultimo_voz and r[1]:        # só silêncio depois dela: serve de resultado final
            texto, confianca = r[1], r[2]
        else:
            try:
                texto, confianca = self.transcrever_detalhado(audio, cfg["voz_modelo_fala"], beam=5,
                                                              prompt=self._dica_vocabulario())
            except Exception as e:
                self.ao_erro(f"o Whisper falhou ({e})")
                return None
        self.ultimo_uso_fala = time.time()
        pico = float(np.max(np.abs(audio))) if len(audio) else 0.0
        registrar(f"fala {len(audio) / TAXA:.1f}s pico={pico:.3f} conf={confianca:.2f} "
                  f"motor={self.ultimo_motor} | {texto}")
        if cfg.get("voz_depurar"):
            self._guardar_audio(audio)
        if not texto:
            return INCERTO
        if " ".join(normalizar(texto)) in FRASES_CANCELAR:
            return None
        if confianca < LIMITE_CONFIANCA:   # o Whisper não tem certeza do que ouviu: melhor perguntar do que mandar bobagem
            self.ao_texto("")
            return INCERTO
        self.ao_texto(texto)
        return texto

    def _guardar_audio(self, audio):
        """voz_depurar: guarda os últimos áudios em ~/.claudinho/voz_debug pra repetir o teste depois."""
        try:
            pasta = Path.home() / ".claudinho" / "voz_debug"
            pasta.mkdir(exist_ok=True)
            with wave.open(str(pasta / (time.strftime("%H%M%S") + ".wav")), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(TAXA)
                w.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
            for velho in sorted(pasta.glob("*.wav"))[:-8]:
                velho.unlink()
        except Exception:
            pass
