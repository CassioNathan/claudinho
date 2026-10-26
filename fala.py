"""A voz do Claudinho (Piper, offline): fala as respostas do chat, uma frase de cada vez.

    falar("Oi!")  → entra na fila; uma thread sintetiza e outra toca (a próxima frase já vai sendo feita enquanto
                    a anterior toca, então a fala sai sem buracos)
    parar()       → corta na hora (você interrompeu, ou desligou a voz) e esvazia a fila
    ocupada       → ainda tem fala na fila ou tocando?

As vozes (~60 MB cada) ficam em ~/.claudinho/vozes; a escolhida carrega em segundo plano (uns 5 s, uma vez só).
"""
import queue
import re
import threading
import time
from pathlib import Path

import numpy as np

VOZES = {  # id do Piper → nome que aparece no painel
    "pt_BR-faber-medium": "Faber",
    "pt_BR-cadu-medium": "Cadu",
    "pt_BR-jeff-medium": "Jeff",
    "pt_BR-edresson-low": "Edresson (mais leve)",
    # Kokoro: um modelo só (~350 MB) com várias vozes; a Dora é feminina de verdade
    "kokoro:pf_dora": "Dora (Kokoro, feminina)",
    "kokoro:pm_alex": "Alex (Kokoro)",
    "kokoro:pm_santa": "Santa (Kokoro)",
}
VOZ_PADRAO = "pt_BR-faber-medium"
ESTILOS = {"normal": "Normal", "anime": "Garotinha de anime 🌸"}   # as vozes do Piper em português são todas masculinas
ANIME_FATOR_KOKORO = 1.25   # a Dora já é feminina: só um toquinho de tom (≈ +4 semitons) pro jeito de anime
ANIME_FATOR = 1.6      # quanto o tom sobe (≈ +8 semitons): o Faber vai de ~150-180 Hz pra ~245 Hz, tom de voz de menina
PASTA = Path.home() / ".claudinho" / "vozes"
KOKORO_PASTA = PASTA / "kokoro"
_KOKORO_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
KOKORO_ARQUIVOS = ("kokoro-v1.0.onnx", "voices-v1.0.bin")
FIM_DE_FRASE = re.compile(r"(?<=[.!?…])\s+|\n+")
EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF\U0000FE0F\U0000200D]")


def eh_kokoro(voz):
    return bool(voz) and voz.startswith("kokoro:")


def instalada(voz):
    if eh_kokoro(voz):
        return all((KOKORO_PASTA / a).exists() for a in KOKORO_ARQUIVOS)
    return (PASTA / f"{voz}.onnx").exists()


def catalogo():
    """As vozes que o painel oferece e quais já estão no PC."""
    return [{"id": v, "nome": nome, "instalada": instalada(v),
             "tamanho": "~350 MB, o modelo vale pras 3 vozes do Kokoro" if eh_kokoro(v) else "~60 MB"}
            for v, nome in VOZES.items()]


def limpar_para_fala(texto):
    """Tira o que não se fala: emoji, markdown, link, bloco de código."""
    texto = re.sub(r"```.*?```", " ", texto, flags=re.S)
    texto = re.sub(r"https?://\S+", " link ", texto)
    texto = EMOJI.sub("", texto)
    texto = re.sub(r"[*_`#>~|]+", "", texto)
    texto = re.sub(r"^\s*[-•]\s+", "", texto, flags=re.M)
    return re.sub(r"\s+", " ", texto).strip()


def dividir_em_frases(texto, minimo=18):
    """Quebra em frases pra falar uma de cada vez (junta as muito curtas, tipo "Oi!", com a seguinte)."""
    frases, atual = [], ""
    for parte in FIM_DE_FRASE.split(texto):
        parte = parte.strip()
        if not parte:
            continue
        atual = f"{atual} {parte}".strip()
        if len(atual) >= minimo:
            frases.append(atual)
            atual = ""
    if atual:
        frases.append(atual)
    return frases


def so_o_comeco(texto, limite):
    """Só as primeiras frases, até ~`limite` letras (pra não ler uma resposta enorme em voz alta)."""
    saida, total = [], 0
    for frase in dividir_em_frases(limpar_para_fala(texto)):
        if saida and total + len(frase) > limite:
            break
        saida.append(frase)
        total += len(frase)
    return " ".join(saida)


def efeito_anime(audio, fator=ANIME_FATOR):
    """Garotinha de anime: a fala é sintetizada mais devagar (length_scale = ANIME_FATOR) e tocada mais rápido, então
    o tom sobe e o ritmo volta ao normal (o timbre fica mais agudo e "pequeno", de brinquedo). Um realce leve nos agudos
    deixa a voz mais brilhante e animada."""
    n = int(len(audio) / fator)
    if n < 2:
        return audio
    novo = np.interp(np.arange(n) * fator, np.arange(len(audio)), audio).astype("float32")
    brilho = novo.copy()
    brilho[1:] += 0.35 * (novo[1:] - novo[:-1])      # realce de agudos (pré-ênfase)
    pico = float(np.max(np.abs(brilho))) or 1.0
    return (brilho / max(1.0, pico / 0.95)).astype("float32")


def efeito_ultron(audio, taxa):
    """Voz de IA vilã: mais grave e metálica (modulação lenta + um eco curtinho)."""
    t = np.arange(len(audio)) / taxa
    metal = audio * (0.72 + 0.28 * np.sin(2 * np.pi * 48 * t))
    atraso = int(taxa * 0.013)
    eco = np.zeros_like(metal)
    eco[atraso:] = metal[:-atraso] * 0.32
    saida = metal + eco
    pico = float(np.max(np.abs(saida))) or 1.0
    return (saida / max(1.0, pico / 0.95)).astype("float32")


class Fala:
    def __init__(self, config):
        """config(): dict com voz_voz, voz_volume (0-100), personalidade (relido a cada frase)."""
        self.config = config
        self.voz = None              # voz do Piper carregada
        self.kokoro = None           # modelo do Kokoro carregado (serve pras 3 vozes dele)
        self.voz_nome = None         # qual voz está carregada
        self.erro = None
        self.carregando = False
        self.baixando = None         # id da voz que está sendo baixada
        self.erro_download = None
        self.para_sintetizar = queue.Queue()
        self.para_tocar = queue.Queue()
        self.versao = 0              # sobe a cada parar(): descarta o que estava sendo preparado
        self.pendentes = 0           # frases que ainda não terminaram de tocar (da versão atual)
        self.trava = threading.Lock()
        self._fios = False

    # ---------- preparo ----------
    def nome_escolhido(self):
        escolhida = self.config().get("voz_voz") or VOZ_PADRAO
        if instalada(escolhida):
            return escolhida
        return next((v for v in VOZES if instalada(v)), None)   # a escolhida sumiu: usa qualquer uma que tenha

    def disponivel(self):
        return self.nome_escolhido() is not None

    def carregar(self):
        """Carrega a voz escolhida em segundo plano (e faz uma síntese de aquecimento: a primeira é bem mais lenta).
        Se a escolha mudou, troca."""
        escolhida = self.nome_escolhido()
        with self.trava:
            if self.carregando or not escolhida or self.voz_nome == escolhida:
                return
            self.carregando = True

        def trabalhar():
            try:
                if eh_kokoro(escolhida):
                    if self.kokoro is None:
                        from kokoro_onnx import Kokoro
                        self.kokoro = Kokoro(str(KOKORO_PASTA / KOKORO_ARQUIVOS[0]), str(KOKORO_PASTA / KOKORO_ARQUIVOS[1]))
                    self.kokoro.create("oi", voice=escolhida.split(":", 1)[1], lang="pt-br")   # aquecimento
                    self.voz = None            # libera a do Piper
                else:
                    from piper import PiperVoice
                    voz = PiperVoice.load(str(PASTA / f"{escolhida}.onnx"))
                    list(voz.synthesize("oi"))
                    self.voz, self.kokoro = voz, None    # e o Kokoro, que é pesado
                self.voz_nome = escolhida
            except Exception as e:
                self.erro = str(e)
            finally:
                self.carregando = False
        threading.Thread(target=trabalhar, daemon=True).start()

    def baixar(self, voz):
        """Baixa uma voz do catálogo (em segundo plano; o painel acompanha por `baixando`)."""
        if voz not in VOZES or self.baixando or instalada(voz):
            return
        self.baixando, self.erro_download = voz, None

        def trabalhar():
            try:
                PASTA.mkdir(parents=True, exist_ok=True)
                if eh_kokoro(voz):
                    self._baixar_kokoro()
                else:
                    from piper.download_voices import download_voice
                    download_voice(voz, PASTA)
            except Exception as e:
                self.erro_download = f"não consegui baixar a voz ({e})"
            finally:
                self.baixando = None
        threading.Thread(target=trabalhar, daemon=True).start()

    def _baixar_kokoro(self):
        """O modelo (~325 MB) e o arquivo de vozes (~28 MB) do Kokoro; baixa pra .part e só então renomeia."""
        import urllib.request
        KOKORO_PASTA.mkdir(parents=True, exist_ok=True)
        for nome in KOKORO_ARQUIVOS:
            destino = KOKORO_PASTA / nome
            if destino.exists():
                continue
            parcial = destino.with_suffix(destino.suffix + ".part")
            with urllib.request.urlopen(_KOKORO_URL + nome, timeout=60) as r, open(parcial, "wb") as saida:
                while True:
                    pedaco = r.read(1 << 20)
                    if not pedaco:
                        break
                    saida.write(pedaco)
            parcial.replace(destino)

    def _iniciar_fios(self):
        if not self._fios:
            self._fios = True
            threading.Thread(target=self._sintetizar, daemon=True).start()
            threading.Thread(target=self._tocar, daemon=True).start()

    # ---------- uso ----------
    @property
    def ocupada(self):
        return self.pendentes > 0

    def _concluir(self, versao):
        with self.trava:
            if versao == self.versao and self.pendentes > 0:
                self.pendentes -= 1

    def falar(self, texto):
        """Põe uma frase (ou um trecho) na fila. Pode chamar várias vezes seguidas."""
        texto = limpar_para_fala(texto)
        if not texto or not self.disponivel():
            return
        self.carregar()
        self._iniciar_fios()
        for frase in dividir_em_frases(texto):
            with self.trava:
                self.pendentes += 1
                versao = self.versao
            self.para_sintetizar.put((versao, frase))

    def parar(self):
        """Interrompido: corta o que está tocando e descarta o que estava na fila."""
        with self.trava:
            self.versao += 1
            self.pendentes = 0
        for fila in (self.para_sintetizar, self.para_tocar):
            while True:
                try:
                    fila.get_nowait()
                except queue.Empty:
                    break
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass

    def esperar(self, limite=60):
        fim = time.time() + limite
        while self.ocupada and time.time() < fim:
            time.sleep(0.05)

    # ---------- threads ----------
    def _sintetizar(self):
        while True:
            versao, frase = self.para_sintetizar.get()
            entregue = False
            try:
                self.carregar()                           # trocou de voz? carrega a nova
                while self.carregando:                    # a voz ainda está carregando: espera
                    time.sleep(0.05)
                if not self.voz_nome or versao != self.versao:
                    continue
                ultron = self.config().get("personalidade") == "ultron"   # o vilão manda mais que o estilo da voz
                anime = not ultron and self.config().get("voz_estilo") == "anime"
                if eh_kokoro(self.voz_nome):
                    fator = ANIME_FATOR_KOKORO if anime else 1.0   # fala mais devagar e depois sobe o tom: o ritmo volta
                    audio, taxa = self.kokoro.create(frase, voice=self.voz_nome.split(":", 1)[1], speed=1.0 / fator,
                                                     lang="pt-br")
                    audio = audio.astype("float32")
                    if anime:
                        audio = efeito_anime(audio, fator)
                else:
                    if anime:
                        from piper import SynthesisConfig
                        ajuste = SynthesisConfig(length_scale=ANIME_FATOR, noise_scale=0.75, noise_w_scale=0.9)
                        pedacos = [c.audio_float_array for c in self.voz.synthesize(frase, ajuste)]
                    else:
                        pedacos = [c.audio_float_array for c in self.voz.synthesize(frase)]
                    if not pedacos or versao != self.versao:
                        continue
                    audio = np.concatenate(pedacos).astype("float32")
                    taxa = self.voz.config.sample_rate
                    if anime:
                        audio = efeito_anime(audio)
                if versao != self.versao:
                    continue
                volume = max(0, min(100, int(self.config().get("voz_volume", 80)))) / 100
                self.para_tocar.put((versao, audio * volume, taxa))
                entregue = True
            except Exception as e:
                self.erro = str(e)
            finally:
                if not entregue:
                    self._concluir(versao)

    def _tocar(self):
        import sounddevice as sd
        while True:
            versao, audio, taxa = self.para_tocar.get()
            if versao != self.versao:
                continue
            try:
                sd.play(audio, taxa)
                fim = time.time() + len(audio) / taxa + 0.3
                while time.time() < fim and versao == self.versao:
                    time.sleep(0.02)
                if versao != self.versao:
                    sd.stop()
                else:
                    time.sleep(0.12)  # respiro entre as frases
            except Exception as e:
                self.erro = str(e)
            finally:
                self._concluir(versao)
