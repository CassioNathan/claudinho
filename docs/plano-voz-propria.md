# Plano: "Minha voz" — o Claudinho falando com a voz que a pessoa mandar

## A ideia

A pessoa manda um áudio (arquivo, vídeo ou link do YouTube) com a voz dela, ou de alguém que deixou, e o Claudinho
passa a falar com essa voz. É **uso pessoal e local**: o áudio, o modelo e a voz ficam só no PC dela, e nada disso vai
no zip da release. Isso aparece como um **aviso** na tela de criar a voz:

> Use a sua voz ou a de alguém que deixou. É só pra uso pessoal, neste PC: não use pra se passar por outra pessoa.

Proteções que custam nada e ficam:

- não tem botão de exportar o áudio gerado: só o Claudinho fala com a voz;
- a marca d'água inaudível do Chatterbox (PerTh) continua em tudo o que ele gera.

## Dois modos

| | Chatterbox direto (pronto) | Piper treinado (a fazer) |
|---|---|---|
| Como funciona | o modelo grande clona na hora a partir de ~10–20 s de áudio | o Chatterbox gera ~400 frases na voz e elas treinam (ajuste fino) uma voz do Piper |
| Onde roda | placa de vídeo (CUDA) | processador, igual às vozes de hoje |
| Memória | ~3,2 GB de VRAM (pico 3,7 GB) | ~60 MB de disco, quase nada de RAM |
| Velocidade (RTX 3050 6 GB) | ~1× tempo real (4,5 s de fala em ~4–6 s); ligar leva ~10–22 s | instantânea, como o Faber |
| Preparar | ~4 s pra tirar a impressão da voz (fica guardada) | ~1h–1h30 de placa: ~30 min gerando, ~30–60 min treinando |
| Pra quem | testar a voz, quem tem placa sobrando | uso no dia a dia |

O modo direto **não serve pro dia a dia** (ocupa metade da placa e leva o tempo da frase pra gerar): ele é o jeito de
ouvir a voz antes e a fábrica de frases do modo treinado.

## O que já está feito (Chatterbox direto)

- **Ambiente à parte**: `~/.claudinho/vozes/clonagem/.venv` (Python 3.11 portátil via `uv`, ~5 GB com o modelo):
  `chatterbox-tts==0.1.7`, `torch 2.6.0+cu124`, `demucs`, `setuptools<81` (sem ele a marca d'água do Chatterbox não carrega:
  `pkg_resources` sumiu do setuptools novo).
- **`voz_propria.py`**: ajudante que roda nesse ambiente. Fala com o `fala.py` por linhas JSON (texto + pasta da voz →
  arquivo `.npy` + taxa). Carrega o modelo na primeira frase, guarda a impressão da voz em `conds.pt` e sai sozinho
  depois de 5 min parado (solta a placa). Vai no executável como arquivo de dados (`claudinho.spec`).
- **`fala.py`**: voz `minha:<nome>` para cada pasta `~/.claudinho/vozes/minhas/<nome>/referencia.wav`. Aparece sozinha na
  lista do painel ("Minha voz: <nome>"), respeita o tom e o volume, e o Ultron continua mandando no tom.
- **Teste**: a voz do Cássio (vídeo com música de fundo → Demucs separou a voz em ~4 s → Chatterbox clonou) ficou boa.

## O que falta

### 1. Criar a voz pelo painel (Jeito dele → Voz → "Minha voz 🎙️")

1. **Aviso** (o texto lá de cima) sempre visível no cartão.
2. **De onde vem o áudio**:
   - arquivo (`.wav`, `.mp3`, `.m4a`, `.mp4`…): o painel sobe o arquivo pro Claudinho (endpoint novo com token);
   - **link do YouTube** + início e fim (ex.: 0:07 a 0:21): o `yt-dlp` baixa só o áudio;
   - gravar no microfone pelo próprio painel (MediaRecorder, 15–30 s, com um texto pra ler).
3. **Preparar**: `ffmpeg` corta e converte → **Demucs** separa a voz da música/ruído (opcional, ligado por padrão) →
   mostra a voz limpa pra ouvir antes de seguir.
4. **Nome da voz** → salva em `~/.claudinho/vozes/minhas/<nome>/referencia.wav` (e `origem.json`: de onde veio, quando).
5. **Ouvir**: o ▶ Ouvir já usa o Chatterbox direto.
6. **Apagar a voz**: tira a pasta inteira (referência, impressão e modelo treinado).

Primeira vez: o Claudinho instala o ambiente (Python portátil + pacotes + modelo, ~5 GB) com barra de progresso,
igual faz com o Ollama e as vozes. Sem placa NVIDIA: avisa que o modo direto fica lento demais e oferece só o treino
(que também precisa de placa) ou nada.

### 2. Modo treinado (Piper) — rodar em casa à noite

1. **Frases**: ~400, em português e variadas. As 127 boas do banco do Claudinho (`frases.py`) + falas típicas dele
   (avisos, respostas curtas, perguntas) + frases foneticamente ricas (todos os sons do português, números, siglas).
2. **Gerar** cada uma com o Chatterbox na voz → WAV 22.050 Hz mono + `metadata.csv` (`id|texto`).
3. **Conferir** com o Whisper (já temos o faster-whisper): transcreve e joga fora o que não bate com o texto
   (o Chatterbox às vezes repete ou engole palavras) e o que é curto/longo demais.
4. **Ajuste fino** a partir do **Faber medium** (`rhasspy/piper-checkpoints`, é **dataset** no Hugging Face, não model:
   `pt/pt_BR/faber/medium/epoch=6159-step=1230728.ckpt`, 846 MB, com o discriminador). Já baixado em
   `~/.claudinho/vozes/clonagem/base/`. Treino: `python -m piper.train fit --data.voice_name ... --data.csv_path
   metadata.csv --data.audio_dir wavs --data.espeak_voice pt-br --data.config_path config.json --data.cache_dir cache
   --data.batch_size 16 --model.sample_rate 22050 --ckpt_path <faber.ckpt> --trainer.max_epochs <N>`.
   - O Piper 1.8 traz o alinhamento (`monotonic_align`) em Cython, que precisa de compilador C++ e nem vem com o
     `core.pyx`. Fiz a mesma conta em **numba** (`monotonic_align/monotonic_align/core.py`): testada, funciona.
     A cópia fica no repositório em `treino_voz/monotonic_core.py` e é colocada no ambiente na instalação.
   - **A conferir primeiro** (treino-teste com ~20 frases): se o checkpoint do Piper antigo (`piper_train`) carrega no
     Piper novo (`piper.train`). Se não carregar: converter o `state_dict` ou treinar com o Piper antigo.
   - Escolher o checkpoint ouvindo (o Piper 1.8 guarda os melhores por `val_mel` e por `val_mos`).
5. **Exportar** pra ONNX (`python -m piper.train.export_onnx`) + `config.json` → `minhas/<nome>/voz.onnx`.
6. **Usar**: a voz `minha:<nome>` passa a preferir o `voz.onnx` (Piper, leve) quando ele existe; o Chatterbox fica só
   pra "ouvir a original" e pra treinar de novo.

No painel: botão **"Treinar versão leve"** com o tempo estimado, rodando em segundo plano (pode fechar o painel),
com progresso (frases geradas, épocas) e um aviso no balão quando terminar. Em jogo/tela cheia, pausa.

### 3. Detalhes

- **A fazer**: modo jogo e Ollama dividem a placa: com o Chatterbox direto e jogo/Ollama aberto, a fala deve cair pra
  voz padrão (hoje ela continua tentando o Chatterbox).
- O ajudante herda o job do Claudinho (fecha junto, que aqui é o certo: não é programa do usuário).
- Tamanhos pra avisar antes: ambiente ~5 GB; checkpoint base 846 MB; voz treinada ~60 MB.
- Licenças: Chatterbox (MIT), Demucs (MIT), Piper e checkpoints (ver MODEL_CARD do Faber), yt-dlp (Unlicense).

## Montar o ambiente em outro PC (ex.: o de casa, pra treinar)

```bash
# Python 3.11 portátil + pacotes, na pasta de dados do Claudinho
mkdir -p ~/.claudinho/vozes/clonagem && cd ~/.claudinho/vozes/clonagem
uv venv --python 3.11 --seed .venv
uv pip install --python .venv/Scripts/python.exe chatterbox-tts==0.1.7 "piper-tts[train]==1.8.0" demucs numba "setuptools<81"   --index-strategy unsafe-best-match --extra-index-url https://download.pytorch.org/whl/cu124
# alinhamento do Piper sem compilador C++
M=.venv/Lib/site-packages/piper/train/vits/monotonic_align/monotonic_align
mkdir -p $M && touch $M/__init__.py && cp <repo>/treino_voz/monotonic_core.py $M/core.py
```

A voz (`~/.claudinho/vozes/minhas/<nome>/referencia.wav`) vai junto copiada do PC onde foi criada.

## Passos (ordem)

1. ~~Chatterbox direto como voz `minha:<nome>` (ajudante + fala.py)~~ ✓
2. Treino-teste com ~20 frases (checkpoint antigo no Piper novo?) — **em casa, à noite**
3. Pipeline completo de treino (frases → gerar → conferir → treinar → exportar) como script
4. Painel: criar a voz (arquivo, link do YouTube, microfone) + aviso + ouvir + apagar
5. Painel: "Treinar versão leve" com progresso
6. Instalação do ambiente sob demanda (Python portátil + pacotes + modelo) pro executável
