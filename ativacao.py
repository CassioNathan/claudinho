"""Palavra de ativação: um modelo pequeno que só sabe ouvir "Ei Claudinho", rodando no microfone o tempo todo.

É o truque da Alexa: em vez de passar toda fala da sala pelo Whisper e procurar "Claudinho" no texto (que acordava
com ruído e perdia chamada), um detector dedicado dá uma nota a cada 80 ms. Só quando ele acha que ouviu a chamada o
Whisper entra, pra confirmar e pegar o resto da frase.

    áudio 16 kHz → melspectrogram.onnx → embedding_model.onnx (os dois do openWakeWord, baixados do GitHub dele)
                 → claudinho.onnx (o nosso, treinado por treino_ativacao/treinar.py) → nota de 0 a 1

Tudo fica em ~/.claudinho/ativacao. Sem o claudinho.onnx (ninguém treinou ainda), `disponivel()` é False e a voz
continua no jeito antigo, só com o Whisper.
"""
import json
import os
import urllib.request
from pathlib import Path

import numpy as np

DADOS = Path(os.environ.get("CLAUDINHO_DADOS") or Path.home() / ".claudinho")
PASTA = DADOS / "ativacao"
MODELO = PASTA / "claudinho.onnx"
INFO = PASTA / "claudinho.json"            # o limiar escolhido no treino e os números da conferência
BASE_URL = "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/"
BASES = ("melspectrogram.onnx", "embedding_model.onnx")
TAXA = 16000
PASSO = 1280                # 80 ms: o detector dá uma nota a cada passo
JANELA_MEL = 76             # quadros de espectrograma por embedding
JANELA = 16                 # embeddings que o classificador olha (~1,3 s)
CONTEXTO = TAXA             # áudio de antes usado pra calcular o espectrograma de cada passo
QUADROS_POR_PASSO = PASSO // 160   # o espectrograma anda 10 ms por quadro: 8 quadros novos a cada passo
LIMIAR_PADRAO = 0.5


def disponivel():
    return MODELO.exists() and all((PASTA / b).exists() for b in BASES)


def baixar_bases():
    """Os dois modelos base do openWakeWord (~2,4 MB). Licença: o espectrograma e o embedding vêm do
    speech_embedding do Google (Apache 2.0)."""
    PASTA.mkdir(parents=True, exist_ok=True)
    for nome in BASES:
        destino = PASTA / nome
        if not destino.exists():
            tmp = destino.with_suffix(".tmp")
            urllib.request.urlretrieve(BASE_URL + nome, tmp)
            os.replace(tmp, destino)


def limiar():
    try:
        return float(json.loads(INFO.read_text(encoding="utf-8")).get("limiar", LIMIAR_PADRAO))
    except (OSError, ValueError, TypeError, AttributeError):
        return LIMIAR_PADRAO


def _sessao(caminho):
    import onnxruntime as ort
    opcoes = ort.SessionOptions()
    opcoes.inter_op_num_threads = opcoes.intra_op_num_threads = 1   # é leve: não disputa CPU com o resto
    return ort.InferenceSession(str(caminho), sess_options=opcoes, providers=["CPUExecutionProvider"])


class Extrator:
    """Áudio → embeddings de 96 números (o mesmo cálculo no treino e no microfone)."""

    def __init__(self, pasta=PASTA):
        self.mel_modelo = _sessao(pasta / BASES[0])
        self.emb_modelo = _sessao(pasta / BASES[1])

    def mel(self, audio_int16):
        x = np.asarray(audio_int16, dtype="float32")[None, :]
        return np.squeeze(self.mel_modelo.run(None, {"input": x})[0]) / 10 + 2   # o ajuste do openWakeWord

    def embeddings_do_mel(self, janelas):
        """janelas: (n, 76, 32) → (n, 96)"""
        x = np.asarray(janelas, dtype="float32")[..., None]
        return self.emb_modelo.run(None, {"input_1": x})[0].reshape(len(janelas), 96)

    def embeddings(self, audio_int16, lote=256):
        """O clipe inteiro: um embedding a cada 8 quadros de espectrograma (80 ms)."""
        espec = self.mel(audio_int16)
        janelas = [espec[i:i + JANELA_MEL] for i in range(0, len(espec) - JANELA_MEL + 1, 8)]
        if not janelas:
            return np.zeros((0, 96), dtype="float32")
        return np.concatenate([self.embeddings_do_mel(janelas[i:i + lote]) for i in range(0, len(janelas), lote)])


class Detector:
    """Recebe blocos do microfone (float de -1 a 1, 16 kHz) e devolve a maior nota dos passos novos."""

    def __init__(self, modelo=MODELO, pasta=PASTA):
        self.extrator = Extrator(pasta)
        self.modelo = _sessao(modelo)
        self.entrada = self.modelo.get_inputs()[0].name
        self.limiar = limiar()
        self.zerar()

    def zerar(self):
        self.bruto = np.zeros(PASSO + CONTEXTO, dtype="int16")   # o último ~1,1 s de áudio
        self.sobra = np.zeros(0, dtype="int16")
        self.espec = np.ones((JANELA_MEL, 32), dtype="float32")
        ruido = np.random.default_rng(0).integers(-1000, 1000, TAXA * 2).astype("int16")
        self.atributos = self.extrator.embeddings(ruido)[-JANELA:]

    def processar(self, bloco):
        """Nota (0 a 1) mais alta entre os passos de 80 ms que este bloco completou; 0 se nenhum completou."""
        audio = np.concatenate([self.sobra, (np.clip(bloco, -1, 1) * 32767).astype("int16")])
        n = len(audio) // PASSO * PASSO
        self.sobra = audio[n:]
        melhor = 0.0
        for i in range(0, n, PASSO):
            self.bruto = np.concatenate([self.bruto[PASSO:], audio[i:i + PASSO]])
            # o espectrograma do passo novo é calculado com 1 s de contexto antes: só com o pedacinho (como o
            # openWakeWord faz) ele sai diferente do calculado no clipe inteiro, que é como o treino vê
            self.espec = np.vstack([self.espec, self.extrator.mel(self.bruto)[-QUADROS_POR_PASSO:]])[-JANELA_MEL:]
            emb = self.extrator.embeddings_do_mel(self.espec[None, -JANELA_MEL:])
            self.atributos = np.vstack([self.atributos, emb])[-JANELA:]
            nota = float(self.modelo.run(None, {self.entrada: self.atributos[None].astype("float32")})[0].reshape(-1)[0])
            melhor = max(melhor, nota)
        return melhor
