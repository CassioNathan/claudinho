"""Pipeline do modo treinado da "Minha voz": frases → Chatterbox clona → Whisper confere → Piper treina → ONNX.

Roda no ambiente da clonagem (~/.claudinho/vozes/clonagem/.venv), em estágios que podem ser interrompidos e retomados
(o que já foi feito é pulado):

    python pipeline.py <voz> gerar          gera as frases com a voz de referência (placa de vídeo, ~40 min p/ 350 frases)
    python pipeline.py <voz> conferir       Whisper confere cada frase e joga fora as que não bateram (processador)
    python pipeline.py <voz> treinar [N]    ajuste fino do Faber com as frases (placa de vídeo), N épocas (padrão 150)
    python pipeline.py <voz> exportar       exporta os melhores checkpoints pra ONNX e fala uma frase com cada
    python pipeline.py <voz> tudo [N]       os quatro, em sequência

Tudo fica em ~/.claudinho/vozes/clonagem/trabalho/<voz>/ ; o progresso, em progresso.json. Prioridade baixa de
processador, pra não pesar o PC; o estágio de gerar pausa quando tem algo em tela cheia (jogo).
"""
import atexit
import ctypes
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import warnings
import wave
from pathlib import Path

warnings.filterwarnings("ignore")
RAIZ = Path(os.environ.get("CLAUDINHO_DADOS") or Path.home() / ".claudinho") / "vozes"   # como o sistema.DADOS
CLONAGEM = RAIZ / "clonagem"
FABER_CKPT = CLONAGEM / "base" / "faber_windows.ckpt"
FABER_CONFIG = RAIZ / "pt_BR-faber-medium.onnx.json"
AQUI = Path(__file__).resolve().parent
TAXA = 22050
MIN_S, MAX_S = 0.8, 16.0          # frase mais curta/longa que isso é descartada (o Chatterbox às vezes engole ou repete)
CONFERENCIA_MINIMA = 0.78         # parecença mínima entre o que o Whisper ouviu e o texto
MIN_FRASES_TREINO = 50            # com menos frases aprovadas que isso, o treino não aprende a voz
EPOCAS_PADRAO, EPOCAS_MAX = 150, 2000
PRIORIDADE_BAIXA = 0x4000         # BELOW_NORMAL_PRIORITY_CLASS: o PC continua leve enquanto treina
FRASES_TESTE = ["Oi, eu sou o Claudinho. Hoje o dia está lindo, vamos programar juntos?",
                "Terminei a tarefa e não apareceu nenhum erro. Quer ver o resultado?",
                "Atenção, existe uma diferença pequena entre essas duas cores."]


def prioridade_baixa():
    try:
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), PRIORIDADE_BAIXA)
    except (AttributeError, OSError):   # fora do Windows: segue com a prioridade normal
        pass


def tela_cheia():
    """Tem algo em tela cheia na frente (jogo, vídeo)? Versão simplificada do teste do Claudinho (motores.tela_cheia):
    aqui não dá pra importar o app, então não ignora as janelas que ele ignora; na dúvida, pausa a mais."""
    try:
        import ctypes.wintypes   # só existe de verdade no Windows (aqui dentro: o módulo importa em qualquer sistema)
        u = ctypes.windll.user32
        hwnd = u.GetForegroundWindow()
        r = ctypes.wintypes.RECT()
        u.GetWindowRect(hwnd, ctypes.byref(r))
        return r.left <= 0 and r.top <= 0 and r.right - r.left >= u.GetSystemMetrics(0) \
            and r.bottom - r.top >= u.GetSystemMetrics(1) and u.GetWindowTextLengthW(hwnd) > 0
    except (AttributeError, OSError, ValueError, ImportError):
        return False


def normalizar(t):
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", t)).strip()


class Trabalho:
    def __init__(self, voz):
        self.voz = voz
        self.pasta = CLONAGEM / "trabalho" / voz
        self.wavs = self.pasta / "wavs"
        self.wavs.mkdir(parents=True, exist_ok=True)
        self.referencia = RAIZ / "minhas" / voz / "referencia.wav"
        self.arq_progresso = self.pasta / "progresso.json"

    def progresso(self, **campos):
        """Anota o andamento. Grava num .tmp e troca de uma vez: Ctrl+C no meio não deixa o arquivo pela metade."""
        try:
            dados = json.loads(self.arq_progresso.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            dados = {}
        dados = dados if isinstance(dados, dict) else {}
        dados.update(campos, atualizado=time.strftime("%H:%M:%S"))
        tmp = self.arq_progresso.with_suffix(".tmp")
        tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.arq_progresso)

    def travar(self):
        """Só um pipeline por voz de cada vez (dois juntos geram as mesmas frases e brigam pela placa de vídeo)."""
        trava = self.pasta / ".rodando"
        try:
            pid = int(trava.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pid = 0
        if pid and pid != os.getpid() and processo_vivo(pid):
            sys.exit(f"já tem um pipeline rodando pra voz {self.voz} (processo {pid}); espere ele terminar")
        trava.write_text(str(os.getpid()), encoding="utf-8")
        atexit.register(lambda: trava.unlink(missing_ok=True))


def processo_vivo(pid):
    """O processo `pid` ainda roda? (Windows: 259 = ainda rodando.)"""
    try:
        k = ctypes.windll.kernel32
    except AttributeError:
        return False
    h = k.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    codigo = ctypes.c_ulong()
    k.GetExitCodeProcess(h, ctypes.byref(codigo))
    k.CloseHandle(h)
    return codigo.value == 259


def escrever_wav(caminho, audio, taxa):
    """Áudio float (-1 a 1) → WAV PCM 16 bits mono."""
    import numpy as np
    pcm = (np.clip(np.asarray(audio, dtype="float32"), -1, 1) * 32767).astype(np.int16)
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(pcm.tobytes())
    return len(pcm) / taxa


def duracao_wav(caminho):
    with wave.open(str(caminho)) as w:
        return w.getnframes() / w.getframerate()


# ---------------------------------------------------------------------------------------------- frases
def montar_frases(t):
    """As frases do treino: o banco do Claudinho (sem as que têm {campo}) + as extras. Ordem fixa: id = posição."""
    destino = t.pasta / "frases.txt"
    if destino.exists():   # linha em branco (editado à mão) não vira frase vazia
        return [linha for linha in destino.read_text(encoding="utf-8").splitlines() if linha.strip()]
    sys.path.insert(0, str(AQUI.parent))
    import frases as banco

    def achatar(o):
        if isinstance(o, str):
            yield o
        elif isinstance(o, dict):
            for v in o.values():
                yield from achatar(v)
        elif isinstance(o, (list, tuple)):
            for v in o:
                yield from achatar(v)
    todas = []
    for nome in ("FRASES", "POR_HORA", "MALDOSAS", "AUTOELOGIO", "ULTRON", "TDAH"):
        todas += [f for f in achatar(getattr(banco, nome, [])) if "{" not in f]
    todas += (AQUI / "frases_extras.txt").read_text(encoding="utf-8").splitlines()
    vistas, saida = set(), []
    for f in (x.strip() for x in todas):
        if 12 <= len(f) <= 170 and normalizar(f) not in vistas:
            vistas.add(normalizar(f))
            saida.append(f)
    destino.write_text("\n".join(saida) + "\n", encoding="utf-8")
    return saida


def salvar_wav(caminho, wav, taxa_origem):
    import torchaudio
    return escrever_wav(caminho, torchaudio.functional.resample(wav.cpu(), taxa_origem, TAXA).squeeze(0).numpy(), TAXA)


# ---------------------------------------------------------------------------------------------- estágio 1
def gerar(t):
    if not t.referencia.exists():
        sys.exit(f"falta a voz de referência: {t.referencia}")
    textos = montar_frases(t)
    pendentes = [(i, f) for i, f in enumerate(textos) if not (t.wavs / f"f{i:04d}.wav").exists()]
    print(f"{len(textos)} frases; {len(textos) - len(pendentes)} já feitas; {len(pendentes)} a gerar", flush=True)
    if not pendentes:
        return
    import torch
    if not torch.cuda.is_available():
        sys.exit("gerar precisa de placa de vídeo NVIDIA (CUDA); sem ela o Chatterbox leva minutos por frase")
    t.progresso(estagio="gerar", total=len(textos), feitas=len(textos) - len(pendentes), inicio=time.strftime("%H:%M:%S"))
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    modelo = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
    t0, feitas = time.time(), len(textos) - len(pendentes)
    for i, frase in pendentes:
        while tela_cheia():                       # jogo na frente: espera (o treino não é urgente)
            t.progresso(estagio="gerar (pausado: tela cheia)")
            time.sleep(10)
        for tentativa in range(3):
            wav = modelo.generate(frase, language_id="pt", audio_prompt_path=str(t.referencia))
            duracao = wav.shape[1] / modelo.sr
            if MIN_S <= duracao <= MAX_S:
                break
        else:
            print(f"  descartada (duração {duracao:.1f}s): {frase}", flush=True)
            (t.wavs / f"f{i:04d}.ruim").write_text(frase, encoding="utf-8")
            continue
        salvar_wav(t.wavs / f"f{i:04d}.wav", wav, modelo.sr)
        feitas += 1
        if feitas % 5 == 0 or feitas == len(textos):
            t.progresso(estagio="gerar", feitas=feitas, total=len(textos),
                        minutos_decorridos=round((time.time() - t0) / 60, 1))
            print(f"  {feitas}/{len(textos)} ({(time.time() - t0) / 60:.1f} min)", flush=True)
    t.progresso(estagio="gerar: terminou", feitas=feitas)


# ---------------------------------------------------------------------------------------------- estágio 2
def conferir(t):
    import numpy as np
    from faster_whisper import WhisperModel
    textos = montar_frases(t)
    if not any((t.wavs / f"f{i:04d}.wav").exists() for i in range(len(textos))):
        sys.exit(f"não tem nenhuma frase gerada pra voz {t.voz}: rode o estágio 'gerar' antes")
    whisper = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=4)
    boas, ruins = [], []
    t.progresso(estagio="conferir", total=len(textos))
    for i, frase in enumerate(textos):
        arq = t.wavs / f"f{i:04d}.wav"
        if not arq.exists():
            continue
        with wave.open(str(arq)) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype("float32") / 32768
        x16 = np.interp(np.arange(0, len(x), TAXA / 16000), np.arange(len(x)), x).astype("float32")
        segs, _ = whisper.transcribe(x16, language="pt", beam_size=2, condition_on_previous_text=False)
        ouvido = " ".join(s.text for s in segs)
        razao = difflib.SequenceMatcher(None, normalizar(ouvido), normalizar(frase)).ratio()
        (boas if razao >= CONFERENCIA_MINIMA else ruins).append((i, frase, ouvido, razao))
        if (i + 1) % 25 == 0:
            print(f"  conferidas {i + 1}/{len(textos)} (boas {len(boas)})", flush=True)
    with open(t.pasta / "metadata.csv", "w", encoding="utf-8", newline="") as f:
        for i, frase, _, _ in boas:
            f.write(f"f{i:04d}|{frase}\n")
    (t.pasta / "rejeitadas.txt").write_text(
        "\n".join(f"f{i:04d} ({r:.2f}) | {frase} | ouvi: {ouvido}" for i, frase, ouvido, r in ruins), encoding="utf-8")
    minutos = sum(duracao_wav(t.wavs / f"f{i:04d}.wav") for i, *_ in boas) / 60
    print(f"{len(boas)} boas ({minutos:.1f} min de voz), {len(ruins)} rejeitadas (ver rejeitadas.txt)", flush=True)
    t.progresso(estagio="conferir: terminou", boas=len(boas), rejeitadas=len(ruins), minutos_de_voz=round(minutos, 1))
    shutil.copy(FABER_CONFIG, t.pasta / "config.json")


# ---------------------------------------------------------------------------------------------- estágio 3
def treinar(t, epocas=EPOCAS_PADRAO):
    metadata = t.pasta / "metadata.csv"
    linhas = [x for x in metadata.read_text(encoding="utf-8").splitlines() if x.strip()] if metadata.exists() else []
    if not metadata.exists():
        sys.exit("rode o estágio 'conferir' antes")
    if len(linhas) < MIN_FRASES_TREINO:
        sys.exit(f"só {len(linhas)} frases aprovadas no metadata.csv; precisa de pelo menos {MIN_FRASES_TREINO}")
    if not (t.pasta / "config.json").exists():
        shutil.copy(FABER_CONFIG, t.pasta / "config.json")
    cmd = [sys.executable, "-m", "piper.train", "fit", "--data.voice_name", t.voz,
           "--data.csv_path", "metadata.csv", "--data.audio_dir", "wavs", "--data.espeak_voice", "pt-br",
           "--data.config_path", "config.json", "--data.cache_dir", "cache", "--data.batch_size", "16",
           "--model.sample_rate", str(TAXA), "--model.warmstart_ckpt", str(FABER_CKPT),
           "--trainer.max_epochs", str(epocas), "--trainer.default_root_dir", "treino"]
    t.progresso(estagio="treinar", epocas=epocas)
    print("treinando:", " ".join(cmd[3:]), flush=True)
    with open(t.pasta / "treino.log", "ab") as log:
        r = subprocess.run(cmd, cwd=t.pasta, stdout=log, stderr=subprocess.STDOUT,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"}, creationflags=PRIORIDADE_BAIXA)
    t.progresso(estagio="treinar: terminou" if r.returncode == 0 else f"treinar: ERRO {r.returncode}")
    if r.returncode:
        sys.exit(f"o treino terminou com erro {r.returncode} (veja treino.log)")


# ---------------------------------------------------------------------------------------------- estágio 4
def nota(nome, metrica):
    """O número da métrica no nome do checkpoint ("epoch=120-val_mel=0.3914.ckpt", e também "5e-05"), ou None."""
    m = re.search(metrica + r"=([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)(?=-|\.ckpt$)", nome)
    return float(m.group(1)) if m else None


def melhores_checkpoints(t):
    """O melhor por val_mel (menor) e o melhor por val_mos (maior), entre os que o Piper guardou."""
    cks = list((t.pasta / "treino").rglob("*.ckpt"))
    por_mel = [(v, c) for c in cks if (v := nota(c.name, "val_mel")) is not None]
    por_mos = [(v, c) for c in cks if (v := nota(c.name, "val_mos")) is not None]
    achados = {}
    if por_mel:
        achados["mel"] = min(por_mel, key=lambda p: p[0])[1]
    if por_mos:
        achados["mos"] = max(por_mos, key=lambda p: p[0])[1]
    return achados


def exportar(t):
    import numpy as np
    from piper import PiperVoice
    saida = t.pasta / "saida"
    melhores = melhores_checkpoints(t)
    if not melhores:
        sys.exit(f"não tem checkpoint treinado pra voz {t.voz}: rode o estágio 'treinar' antes")
    saida.mkdir(exist_ok=True)
    for nome, ck in melhores.items():
        onnx = saida / f"{t.voz}_{nome}.onnx"
        print(f"exportando {ck.name} → {onnx.name}", flush=True)
        r = subprocess.run([sys.executable, str(AQUI / "exportar_onnx.py"), "--checkpoint", str(ck),
                            "--output-file", str(onnx)], capture_output=True, creationflags=PRIORIDADE_BAIXA)
        if r.returncode:
            motivo = (r.stderr or b"").decode("utf-8", "replace").strip().splitlines()[-5:]
            sys.exit(f"não consegui exportar {ck.name}:\n" + "\n".join(motivo))
        shutil.copy(t.pasta / "config.json", str(onnx) + ".json")
        voz = PiperVoice.load(str(onnx))
        for k, frase in enumerate(FRASES_TESTE, 1):
            audio = np.concatenate([c.audio_float_array for c in voz.synthesize(frase)])
            escrever_wav(saida / f"amostra_{nome}_{k}.wav", audio, voz.config.sample_rate)
    t.progresso(estagio="exportar: terminou", checkpoints={k: v.name for k, v in melhores_checkpoints(t).items()})
    print("pronto: ouça as amostras em", saida, flush=True)


def main():
    if len(sys.argv) < 3 or sys.argv[2] not in ("gerar", "conferir", "treinar", "exportar", "tudo"):
        sys.exit(__doc__)
    epocas = EPOCAS_PADRAO
    if len(sys.argv) > 3:   # confere antes de criar qualquer pasta
        try:
            epocas = int(sys.argv[3])
        except ValueError:
            sys.exit(f"épocas tem que ser um número inteiro, não '{sys.argv[3]}'")
        if not 1 <= epocas <= EPOCAS_MAX:   # -1 no Lightning é treinar pra sempre
            sys.exit(f"épocas tem que estar entre 1 e {EPOCAS_MAX}")
    prioridade_baixa()
    t, estagio = Trabalho(sys.argv[1]), sys.argv[2]
    t.travar()
    if estagio in ("gerar", "tudo"):
        gerar(t)
    if estagio in ("conferir", "tudo"):
        conferir(t)
    if estagio in ("treinar", "tudo"):
        treinar(t, epocas)
    if estagio in ("exportar", "tudo"):
        exportar(t)


if __name__ == "__main__":
    main()
