"""Comando por voz do Claudinho: chamou pelo apelido, o chat abre e ele escuta, digitando o que você fala.

Tudo local: um detector de voz leve (Silero, que vem junto do faster-whisper) fica ouvindo o microfone, e só
quando alguém fala ele passa aquele pedacinho de áudio pra um Whisper pequeno, que vê se tem o apelido. Os
apelidos são só texto (sem treinar nada): a comparação é aproximada, então "Cloudinho" ainda vale.

    ouvindo apelido → (chamou) carrega o Whisper melhor, abre o chat e faz "tuk-tuk" → você fala, o texto vai
    aparecendo → ficou em silêncio: "tuk" mais grave e o texto é enviado.

Quem usa só entrega os callbacks (que rodam na thread da voz: o Claudinho joga tudo numa fila pra thread da tela).
"""
import difflib
import io
import queue
import re
import threading
import time
import unicodedata
import wave

import numpy as np

TAXA = 16000
BLOCO = 2048                    # 128 ms por bloco do microfone
SEG_BLOCO = BLOCO / TAXA
FRASES_CANCELAR = {"cancela", "cancelar", "cancelado", "esquece", "esqueca", "deixa pra la", "deixa quieto"}
ALUCINACOES = ("legendas pela comunidade", "amara.org", "obrigado por assistir", "inscreva-se")


def normalizar(texto):
    """minúsculas, sem acento nem pontuação: o que o Whisper escreve e o que você digitou ficam comparáveis"""
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", texto).split()


def achar_apelido(texto, apelidos, minimo=0.78):
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
            janela = " ".join(norm[i:i + n]).strip()
            if janela and difflib.SequenceMatcher(None, janela, " ".join(alvo)).ratio() >= corte:
                resto = " ".join(palavras[i + n:]).strip(" ,.;:!?-–…")
                return True, resto
    return False, ""


def _tom(frequencias, ms=45, volume=0.35):
    """WAV curtinho na memória: um 'tuk' por frequência, com o som caindo rápido (parece um toque, não um bip)."""
    pedacos = []
    for f in frequencias:
        t = np.arange(int(TAXA * ms / 1000)) / TAXA
        onda = np.sin(2 * np.pi * f * t) * np.exp(-t * 55) * volume
        pedacos += [onda, np.zeros(int(TAXA * 0.035))]
    dados = (np.concatenate(pedacos) * 32767).astype("<i2").tobytes()
    saida = io.BytesIO()
    with wave.open(saida, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes(dados)
    return saida.getvalue()


SONS = {
    "pronto": _tom([880, 1320]),     # tuk-tuk subindo: pode falar
    "enviado": _tom([660, 440]),     # tuk-tuk descendo: parei de ouvir, vou responder
    "cancelado": _tom([330]),
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


def tocar(nome):
    try:
        import winsound
        winsound.PlaySound(SONS[nome], winsound.SND_MEMORY | winsound.SND_ASYNC)
    except Exception:
        pass


class Voz:
    def __init__(self, config, ao_acordar, ao_texto, ao_enviar, ao_cancelar, pausado=lambda: False, ao_erro=print):
        """config(): dict com voz_apelidos, voz_silencio, voz_microfone, voz_modelo_apelido, voz_modelo_fala,
        voz_sons (relido a cada uso: mudar no painel vale na hora)."""
        self.config = config
        self.ao_acordar, self.ao_texto, self.ao_enviar = ao_acordar, ao_texto, ao_enviar
        self.ao_cancelar, self.pausado, self.ao_erro = ao_cancelar, pausado, ao_erro
        self.fila = queue.Queue(maxsize=200)
        self.rodando = False
        self.fio = None
        self.modelos, self.trava_modelos = {}, threading.Lock()
        self.vad = None
        self.estado = "parado"      # parado | ouvindo_apelido | acordando | ouvindo_fala | enviando
        self.ultimo_uso_fala = 0.0

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

    def transcrever(self, audio, modelo, gpu=False, prompt=None):
        segmentos, _ = self._whisper(modelo, gpu).transcribe(
            audio, language="pt", beam_size=1, condition_on_previous_text=False, vad_filter=False,
            initial_prompt=prompt, temperature=0.0, no_speech_threshold=0.5)
        texto = " ".join(s.text.strip() for s in segmentos).strip()
        if any(a in texto.lower() for a in ALUCINACOES):
            return ""
        return texto

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
        p = self.vad(np.ascontiguousarray(janela[-n:]), 512)
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

    def _ao_receber(self, dados, frames, tempo, status):
        try:
            self.fila.put_nowait(dados[:, 0].copy())
        except queue.Full:
            pass

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
        while self.rodando:
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
            tem_voz = self._prob_voz(janela) > 0.5
            if tem_voz:
                if not segmento:
                    segmento = list(pre)
                segmento.append(bloco)
                silencio = 0
            elif segmento:
                segmento.append(bloco)
                silencio += 1
            else:
                pre = (pre + [bloco])[-4:]
            fim = bool(segmento) and (silencio >= 4 or len(segmento) > 8 / SEG_BLOCO)
            if fim:
                audio = np.concatenate(segmento)
                segmento, silencio, pre = [], 0, []
                if len(audio) > 0.25 * TAXA:
                    self._checar_apelido(audio)
                janela = janela[:0]

    # ---------- apelido ----------
    def _checar_apelido(self, audio):
        cfg = self.config()
        apelidos = [a for a in cfg["voz_apelidos"] if a.strip()]
        if not apelidos:
            return
        try:
            texto = self.transcrever(audio, cfg["voz_modelo_apelido"], prompt=", ".join(apelidos) + ".")
        except Exception as e:
            self.ao_erro(f"o Whisper falhou ({e})")
            return
        achou, resto = achar_apelido(texto, apelidos)
        if achou:
            self._conversar(resto)

    # ---------- a conversa ----------
    def _conversar(self, inicio):
        """Chamou: abre o chat, carrega o Whisper melhor, faz 'tuk-tuk' e fica ouvindo até você calar."""
        cfg = self.config()
        self.estado = "acordando"
        if not self.ao_acordar():  # o Claudinho não pode agora (pensando, vendo outra coisa)
            self.estado = "ouvindo_apelido"
            return
        gpu = False  # GPU precisaria de cuBLAS/cuDNN à parte: fica na CPU (não pesa em jogo nem toma VRAM)
        try:
            self._whisper(cfg["voz_modelo_fala"], gpu)  # a "carregadinha" de 1-2 s: o sinal só vem depois dela
            self.ultimo_uso_fala = time.time()
        except Exception as e:
            self.ao_erro(f"não consegui carregar o Whisper ({e})")
            self.estado = "ouvindo_apelido"
            self.ao_cancelar()
            return
        if inicio:  # "Claudinho, que horas são?" numa frase só: já tem pergunta, é só mandar
            self.ao_texto(inicio)
            self._enviar(inicio)
            return
        if cfg.get("voz_sons", True):
            tocar("pronto")
        time.sleep(0.45)    # o próprio tuk-tuk não pode entrar no que ele escuta
        self._limpar_fila()
        self.estado = "ouvindo_fala"
        buffer, falou, silencio, desde = [], False, 0, time.time()
        janela = np.zeros(0, dtype="float32")
        ultimo_parcial, ultimo_texto = 0, ""
        while self.rodando:
            try:
                bloco = self.fila.get(timeout=0.5)
            except queue.Empty:
                continue
            cfg = self.config()
            janela = np.concatenate([janela, bloco])[-TAXA:]
            tem_voz = self._prob_voz(janela) > 0.5
            if tem_voz:
                falou, silencio = True, 0
            elif falou:
                silencio += 1
            if falou:
                buffer.append(bloco)
            decorrido = time.time() - desde
            if not falou and decorrido > 8:           # chamou e não falou nada
                break
            if falou and tem_voz and len(buffer) - ultimo_parcial >= 8:  # texto aparecendo enquanto fala
                ultimo_parcial = len(buffer)
                try:
                    ultimo_texto = self.transcrever(np.concatenate(buffer), cfg["voz_modelo_apelido"])
                    self.ao_texto(ultimo_texto)
                except Exception:
                    pass
            if falou and silencio * SEG_BLOCO >= float(cfg.get("voz_silencio", 1.2)):
                break
            if decorrido > 90:
                break
        if not falou or not buffer:
            self._cancelar()
            return
        self._enviar_audio(np.concatenate(buffer), gpu)

    def _enviar_audio(self, audio, gpu):
        cfg = self.config()
        self.estado = "enviando"
        if cfg.get("voz_sons", True):
            tocar("enviado")  # parou de ouvir
        try:
            texto = self.transcrever(audio, cfg["voz_modelo_fala"], gpu)
        except Exception as e:
            self.ao_erro(f"o Whisper falhou ({e})")
            texto = ""
        self.ultimo_uso_fala = time.time()
        if not texto or " ".join(normalizar(texto)) in FRASES_CANCELAR:
            self._cancelar(som=False)
            return
        self.ao_texto(texto)
        self._enviar(texto, som=False)

    def _enviar(self, texto, som=True):
        if som and self.config().get("voz_sons", True):
            tocar("enviado")
        self.ao_enviar(texto)
        self._limpar_fila()
        self.estado = "ouvindo_apelido"

    def _cancelar(self, som=True):
        if som and self.config().get("voz_sons", True):
            tocar("cancelado")
        self.ao_cancelar()
        self._limpar_fila()
        self.estado = "ouvindo_apelido"
