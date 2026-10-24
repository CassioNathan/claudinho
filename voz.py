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
import zlib
from pathlib import Path

import numpy as np

TAXA = 16000
BLOCO = 2048                    # 128 ms por bloco do microfone
SEG_BLOCO = BLOCO / TAXA
FRASES_CANCELAR = {"cancela", "cancelar", "cancelado", "esquece", "esqueca", "deixa pra la", "deixa quieto",
                   "tchau", "encerrar", "encerra", "pode encerrar", "chega", "fim"}
INCERTO = object()               # o Whisper não entendeu: pede pra repetir em vez de mandar
LIMITE_CONFIANCA = -1.0         # log-prob médio abaixo disso = chute
LIMIAR_VOZ = 0.4                # abaixo do 0,5 padrão: pega voz baixa ou longe do microfone
ESPERA_INICIAL = 8.0            # chamou e não falou nada: desiste depois disso
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


def preparar(audio):
    """Microfone baixo ou longe: tira o DC e sobe o volume até o pico ficar em ~0,6 (no máximo 40x). Áudio quase
    mudo (só ruído de fundo) fica como está pra não virar chiado alto."""
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
                 ao_estado=lambda e: None, conversa_viva=lambda: True):
        """config(): dict com voz_apelidos, voz_silencio, voz_microfone, voz_modelo_apelido, voz_modelo_fala,
        voz_sons (relido a cada uso: mudar no painel vale na hora)."""
        self.config = config
        self.ao_acordar, self.ao_texto, self.ao_enviar = ao_acordar, ao_texto, ao_enviar
        self.ao_cancelar, self.pausado, self.ao_erro = ao_cancelar, pausado, ao_erro
        self.ao_estado, self.conversa_viva = ao_estado, conversa_viva
        self.resposta = threading.Event()   # o Claudinho avisa (resposta_chegou) quando terminou de responder
        self.fila = queue.Queue(maxsize=200)
        self.rodando = False
        self.fio = None
        self.modelos, self.trava_modelos = {}, threading.Lock()
        self.trava_transcricao = threading.Lock()
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

    def transcrever_detalhado(self, audio, modelo, prompt=None, beam=3):
        """(texto, confiança): confiança é a média do log-prob dos trechos (0 = certeza; < -1 = chute) e vira -5 se
        o Whisper achou que não era fala. Texto vazio quando parece alucinação (repetição, legenda inventada)."""
        audio = preparar(audio)
        with self.trava_transcricao:
            segmentos, _ = self._whisper(modelo).transcribe(
                audio, language="pt", beam_size=beam, condition_on_previous_text=False, vad_filter=False,
                initial_prompt=prompt, temperature=[0.0, 0.2, 0.4], compression_ratio_threshold=2.2,
                log_prob_threshold=-1.2, no_speech_threshold=0.6, repetition_penalty=1.1)
            segmentos = list(segmentos)
        texto = " ".join(s.text.strip() for s in segmentos).strip()
        if not segmentos or any(a in texto.lower() for a in ALUCINACOES) or repetitivo(texto):
            return "", -9.0
        logprob = float(np.mean([s.avg_logprob for s in segmentos]))
        sem_fala = float(np.max([s.no_speech_prob for s in segmentos]))
        return texto, (logprob if sem_fala < 0.6 else -5.0)

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
            tem_voz = self._prob_voz(janela) > LIMIAR_VOZ
            if tem_voz:
                if not segmento:
                    segmento = list(pre)
                segmento.append(bloco)
                silencio = 0
            elif segmento:
                segmento.append(bloco)
                silencio += 1
            else:
                pre = (pre + [bloco])[-6:]
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
        self.ao_estado("preparando")
        if not self.ao_acordar():  # o Claudinho não pode agora (pensando, vendo outra coisa)
            self.estado = "ouvindo_apelido"
            self.ao_estado("fim")
            return
        try:
            self._whisper(cfg["voz_modelo_fala"])  # a "carregadinha" de 1-2 s: o sinal só vem depois dela
            self.ultimo_uso_fala = time.time()
        except Exception as e:
            self.ao_erro(f"não consegui carregar o Whisper ({e})")
            self.estado = "ouvindo_apelido"
            self.ao_estado("fim")
            self.ao_cancelar()
            return
        espera, primeira = ESPERA_INICIAL, True
        while self.rodando and self.conversa_viva():
            if not (primeira and inicio):  # "Claudinho, que horas são?" numa frase só: já tem pergunta
                self.ao_estado("ouvindo")
                self._sinal("pronto")
                time.sleep(0.45)    # o próprio tuk-tuk não pode entrar no que ele escuta
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
        self._encerrar(primeira)

    def _encerrar(self, sem_resposta):
        """Fim da conversa por voz: volta a escutar só o apelido."""
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
        tr = {"rodando": False, "ativo": True, "resultado": None}   # a thread do texto parcial

        def transcrever_em_paralelo(audio, n, beam):
            try:
                texto, conf = self.transcrever_detalhado(audio, modelo, beam=beam)
                if tr["ativo"]:
                    if texto and conf >= LIMITE_CONFIANCA:
                        self.ao_texto(texto)
                    tr["resultado"] = (n, texto, conf)
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
            tem_voz = self._prob_voz(janela) > LIMIAR_VOZ
            if tem_voz:
                falou, silencio = True, 0
            elif falou:
                silencio += 1
            if falou:
                buffer.append(bloco)
            else:
                pre = (pre + [bloco])[-6:]
            if tem_voz and len(buffer) == 1:
                buffer = pre + buffer
            if tem_voz:
                ultimo_voz = len(buffer)
            if not falou and decorrido > espera:       # contador de encerrar (ou de desistir da chamada)
                tr["ativo"] = False
                return None
            if falou and not tr["rodando"]:
                if tem_voz and len(buffer) - feito_ate >= 12:                       # falando: texto aparecendo
                    disparar(beam=1)
                elif not tem_voz and silencio >= 5 and feito_ate < ultimo_voz:    # pausou: já vai o caprichado
                    disparar(beam=3)
            if falou and silencio * SEG_BLOCO >= float(cfg.get("voz_silencio", 2.5)):  # contador de enviar
                break
            if decorrido > 90:
                break
        if not falou or not buffer:
            tr["ativo"] = False
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
                texto, confianca = self.transcrever_detalhado(audio, cfg["voz_modelo_fala"], beam=5)
            except Exception as e:
                self.ao_erro(f"o Whisper falhou ({e})")
                return None
        self.ultimo_uso_fala = time.time()
        pico = float(np.max(np.abs(audio))) if len(audio) else 0.0
        registrar(f"fala {len(audio) / TAXA:.1f}s pico={pico:.3f} conf={confianca:.2f} "
                  f"modelo={cfg['voz_modelo_fala']} | {texto}")
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
