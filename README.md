# Claudinho

Mascote de mesa em pixel art que mora na tela do Windows, feito em Python, com o jeitinho do Darwin
(O Incrível Mundo de Gumball): animado, inocente e sempre querendo ajudar. Ele passeia, corre entre monitores
atrás do mouse, conversa com você por texto ou voz usando o Claude Code, avisa quando seus chats do Claude Code
terminam e comenta o que está na tela.

Também dá uma mão no dia a dia: abre programas e projetos (esperando o programa carregar de verdade), aperta
os atalhos que você ensina no painel e repete rotinas que você grava em sites pela extensão do navegador.
Tudo que mexe no PC segue regras claras: o que é seguro ele faz, o resto pede **Pode / Não** e o que é
destrutivo ele recusa. A voz e a memória ficam no seu PC.

## O que ele faz

- **Chat rápido:** clique nele e pergunte. A resposta vem num balão com o campo pra continuar a conversa.
  Ele lembra do que acabou de falar nos balões: clicou logo depois de uma piada ou aviso, a conversa
  abre nela e dá pra responder direto ("ué, por que pão de queijo?").
  Usa o Claude Code instalado no PC (Haiku com pensamento leve), com a sua memória e o seu perfil.
- **Mexe no PC com confirmação:** abre site, pesquisa ou programa da lista sem perguntar (via `abrir.py`);
  qualquer outro comando ou mudança em arquivo pede **Pode / Não** num balão.
- **Pastas e projetos que ele lê sem perguntar** (painel → Privacidade): adicione uma pasta ou clique em
  **🧩 Puxar projetos do Claude**, que lista os projetos que você já abriu no Claude (app ou terminal, lidos do
  `~/.claude.json`) pra você marcar quais liberar. Ler fica livre; mudar arquivo ou rodar comando continua pedindo.
- **Avisos em fila:** quando um chat do Claude Code termina, ele avisa (projeto, o que foi pedido, resposta).
  Sua pergunta tem prioridade; os avisos esperam e somem sozinhos.
  O que ele fala nos balões (avisos, dicas do Júnior, resumos) entra na conversa: vai inteiro junto da sua próxima
  mensagem e, se você responde abrindo o balão de uma fala, o chat sabe que é resposta àquela fala.
- **Piadas sobre a tela:** banco de frases + Haiku olhando um print. Modo TDAH 🐿️ (o deboche maldoso 😈 é o jeito do Ultron),
  avaliação boa/ruim (ele aprende), memória do dia e **faixa nos olhos 🙈** (aí não tira print).
- **Modo Júnior 🧑‍💻:** em vez de piada, ele lê a janela em que você está com o OCR do próprio Windows (local, de graça)
  e só chama a IA quando aparece um erro novo ou quando o mesmo erro fica na tela por 8 minutos (empacou). A dica vem
  com a janela nítida e o texto lido, e tem botões: **explica** e **corrige** levam o print pro chat, 👎 faz ele largar
  o assunto. Pula programas bloqueados, as janelas dele e respeita a faixa nos olhos.
- **Música:** sabe o que está tocando (Spotify, YouTube no navegador etc., pelos controles de mídia
  do Windows), zoa a música de vez em quando, comenta quando começa uma música nova (curiosidade sobre
  a banda/estilo ou cantarolando com ♪, nunca a letra) e controla o player: no menu (⏯ ⏭ ⏮) ou pedindo no chat
  ("pausa", "pula essa"), sem confirmação (via `musica.py`).
- **Reações com emojis:** de vez em quando sobe um emoji em pixel art do lado dele (café, bug, lâmpada,
  coração, zzz, check, fogo, nota, ?, raio, disquete, suor), às vezes com uma frase, escolhido pelo que
  você está fazendo. Pra criar novos, é só desenhar em `emojis.py`.
- **Sprites:** andando, correndo entre monitores, notebook digitando, pensando, sendo carregado, vendado.
- **Atalhos:** `Win+Y` comenta a tela na hora; `Win+Shift+Y` põe/tira a faixa nos olhos;
  `Win+Shift+E` manda um print da janela da frente pro chat e ele resume/explica bem simplificado
  (dá pra continuar perguntando sobre o mesmo print);
  `Win+Shift+N` resume as notificações da central do Windows, com botão pra limpar as que ele leu.
  O menu (botão direito nele ou no ícone da bandeja) tem só o do dia a dia: perguntar, música, o que tem atalho
  e **Configurações e skins ⚙️**.
- **Painel:** uma janelinha (HTML servido pelo próprio Claudinho, aberta como app do Edge em modo InPrivate)
  com tudo que é configuração: movimento, piadas, esquetes (dá pra rodar qualquer uma na hora), música e extras,
  ações e atalhos. A API dele só aceita pedidos com o token embutido na página.
- **Voz 🎤🔊:** chame por uma frase ("Ei Claudinho", configurável, só texto) e o chat abre ouvindo, com uma faixa de áudio ao vivo. Tudo local:
  Whisper (faster-whisper) escuta e o Piper fala. A conversa é contínua: ele responde falando (já na primeira frase),
  volta a ouvir sozinho e encerra depois de um tempo sem você falar. Um controle de tom deixa qualquer voz mais aguda.
  Ele fala qualquer resposta do chat (o 🔊 do balão liga e desliga; na digitada só o começo é falado) e dá pra escolher a voz. A voz (~60 MB) fica em `~/.claudinho/vozes`
  (`python -m piper.download_voices pt_BR-faber-medium --download-dir ~/.claudinho/vozes`).
- **Skins:** uma cor (12, incluindo arco-íris e peixinho) e um adereço por espaço (cabeça, olhos, rosto, pescoço,
  braços, pés), 34 adereços e 11 pacotes prontos (emo, CEO, natal, cowboy, pirata, anjinho, diabinho, gamer, Ultron,
  rei e o **Peixinho 🐟**: laranja de peixinho dourado, olhões, boquinha, nadadeiras e tênis, inspirado no Darwin de
  O Incrível Mundo de Gumball). Calçado (pés) pinta o pezinho de cada perna, que sobe e desce andando.
  Adereço com "frente" (franja, aba do boné, tapa-olho…) vira pro lado em que ele está olhando.
  Tudo em `skins.py`; adereço novo é só uma lista de pixels.
- **Esquetes (à toa):** de vez em quando, parado, ele apronta: "Tive uma ideia!", saca o notebook,
  trabalha e conta o resultado (às vezes um app novo, às vezes "acabaram meus tokens"); deploy do nada,
  git push --force suando, café, cochilo, alongamento, dancinha, caça ao bug (aparece uma joaninha,
  ele vai lá e come: "Removi um bug 😄"), build quebrado com nuvem de chuva, servidor pegando fogo,
  patinho de borracha, npm install que vira caixa gigante, pizza (só de noite), joguinho, faxina de
  código morto, reunião que podia ser e-mail, bug que vira borboleta e malhação. Piadas e esquetes
  dividem o mesmo tempo (uma fila só, cerca de 1 em 3 vezes é esquete); clicar, arrastar ou chegar algo
  importante interrompe a esquete na hora.
- **YouTube Music 🎵:** no chat ("toca Helena do MCR", "bota um Trivium") ou no painel, ele acha a música
  (ytmusicapi, sem login) e toca num rádio que segue com parecidas. Pausa o que estava tocando antes.
  Play/pausa/próxima/anterior continuam pelos controles de mídia do Windows.
- **Listas e escolha 🎸🎬:** "quais as músicas do Trivium?" → ele lista as mais ouvidas (YouTube Music) e
  pergunta qual tocar; "acha uns vídeos de X" → lista 5 vídeos do YouTube (título, canal, duração) e pergunta qual
  abrir. Também toca suas curtidas e controla o player (aleatório, repetir, volume) e o vídeo (velocidade,
  avançar/voltar, legenda, modo cinema) — esses controles precisam da extensão.
- **Extensão do navegador 🧩** (`extensao/`, instala pelo painel): com ela, a música troca **na aba do YouTube Music
  que já está aberta** (sem aba nova), ele curte a música e "abre no YouTube" pesquisa e entra no primeiro vídeo da
  aba do YouTube. O fundo da extensão pergunta ao Claudinho (127.0.0.1) a cada segundo, com uma chave própria
  (`~/.claudinho/ext_token`); só navega dentro de music.youtube.com e www.youtube.com. Sem extensão ou sem aba
  aberta, abre aba nova como antes. O navegador exige o modo do desenvolvedor ligado pra extensão carregada de pasta.
- **Personalidade 🐟🤖:** no painel, "Claudinho" (o padrão: o jeito do Darwin, de O Incrível Mundo de Gumball, doce,
  ingênuo, empolgado e orgulhoso de um jeito inocente; `JEITO` e `QUEM` no `claudinho.pyw`) ou "Ultron" (IA vilã
  teatral, frases próprias): muda o tom das piadas
  do Haiku, o banco de frases e o jeito de falar no chat (que continua ajudando de verdade; vai nas instruções fixas
  do chat, sem custo por mensagem). Combina com a cor Metal de olhos vermelhos / pacote Ultron.
- **Autoconfiança 😎:** ele sabe como está (cor, adereços, venda) e onde aparece no print. De vez em quando a
  piada é ele se gabando (no Haiku e no banco de frases), comenta quando você troca a roupa dele, e se aparecer o
  logo do Claude/Claude Code na tela ele reage ("esse sou eu", "meu irmão gêmeo", "isso é um espelho?").
- **Motor de IA 🧠** (painel → Sistema): quem pensa no chat, nas piadas olhando a tela e nos resumos —
  **Claude Code** (instalado e logado), **chave da API da Anthropic** (Haiku 5.5 no dia a dia, Sonnet 5.5 no resumo de
  tela; a chave fica criptografada pelo Windows), **IA local** pelo Ollama (leve `qwen3:1.7b` só texto, ou o maior
  `gemma3:4b` que enxerga a tela; não roda com jogo/tela cheia ou placa de vídeo cheia) ou **nenhum**. Tudo em `motores.py`.
- **Mini cérebro 🧠:** cada aviso do Claude Code (pedido + resultado) e cada troca do chat viram lembrança no
  SQLite, com busca de texto local (FTS5). Ao perguntar algo parecido com o que já rolou, até 3 lembranças curtas
  (~250 tokens) vão junto; sem nada parecido, não vai nada. Guardar e buscar não usa IA nenhuma. Liga/desliga no painel.
- **Formatação:** os balões convertem o markdown das respostas (tabela vira lista, títulos, negrito, crases e links somem).
- **Prioridade das falas:** aviso, coisa que você pediu e erro nunca são atropelados (nem enquanto você lê);
  piada sai da frente pra eles; mensagem de estado (vendei, modo ligado…) é descartável e é trocada na hora. Liga/desliga no menu; "Esquete agora 🎭" roda uma na hora.
  Pra testar uma específica: `CLAUDINHO_ESQUETE=inseto` antes de abrir.
- **Conversa:** no balão dá pra anexar um print (aparece uma miniatura dele) da janela que você está usando e abrir
  "ver conversa" com o histórico inteiro. Notificação ou outro programa pulando na frente não fecha
  a conversa; só clicar fora.

## Instalar (quem só quer usar)

Baixe o `Claudinho-<versão>-windows.zip` em **Releases**, descompacte onde quiser e abra o `Claudinho.exe`.
Não precisa de Python. Na primeira vez ele abre o painel com um **passo a passo**: o que ele sabe fazer, quem é você,
o visual, se ele faz piada, vira Júnior ou fica quietinho, o motor de IA, a voz, o que ele pode ler (dá pra liberar os
projetos do Claude ali mesmo) e as opções do PC. Dá pra pular e rever depois em **Sistema**.

- O chat, as piadas olhando a tela e os resumos usam o [Claude Code](https://claude.com/claude-code)
  (instale, rode `claude` e faça `/login`). Sem ele, o resto funciona: banco de frases, música, esquetes, skins.
  Se o login do Claude Code vencer, ele avisa num balão "🔑 preciso de login" com um botão que abre o `claude` num
  terminal pra você fazer o `/login` de novo.
- **Atualizar:** quando sai versão nova ele avisa num balão (olha a última release no GitHub ao abrir e a cada 12 h;
  dá pra desligar em Sistema). Feche o Claudinho, troque a pasta pela do zip novo e abra: seus dados ficam.
- Pra desinstalar: desligue as opções em Sistema, feche (botão direito > Sair) e apague a pasta.
  Os dados ficam em `%USERPROFILE%\.claudinho`.
- Sem assinatura digital, o Windows pode mostrar "O Windows protegeu o computador": "Mais informações" > "Executar assim mesmo".

## Desenvolver / gerar a release

Precisa de Python 3.11+. Pra rodar do código:

```bash
git clone https://github.com/CassioNathan/claudinho.git
cd claudinho
python instalar.py --iniciar   # dependências, hook e atalho de inicialização
```

Pra gerar a release: `pip install pyinstaller` e `python empacotar.py` → `dist/Claudinho/` (dois exes: o
`Claudinho.exe` e o `claudinho-cli.exe`, o ajudante que o chat e o hook usam) e o zip em `release/`.
A versão fica em `sistema.py` (`VERSAO`).

## Onde fica cada coisa

| Arquivo | O que é |
|---|---|
| `claudinho.pyw` | o mascote (janela, sprites, balões, chat, piadas, bandeja) |
| `frases.py` | banco de frases (edite à vontade) |
| `janelas.py` | lê as janelas abertas no Windows |
| `atualizacao.py` | olha a última release no GitHub e diz se tem versão nova (só leitura; quem atualiza é você) |
| `junior.py` | olhos do modo Júnior: OCR do Windows na janela em foco, erro novo e empacado |
| `abrir.py` | ajudante limitado: só abre site, pesquisa ou programa da lista |
| `emojis.py` | pacote de reações em pixel art (desenhos, cores, frases e quando aparecem) |
| `musica.py` | o que está tocando + tocar/pausar/próxima/anterior |
| `hook/claudinho_notificar.py` | hook "Stop" do Claude Code que manda os avisos |
| `instalar.py` | instalação pra quem roda do código |
| `sistema.py` | versão, caminhos (código ou empacotado), atalho de inicialização e o aviso do Claude Code |
| `cli.py` | o ajudante de linha de comando (vira `claudinho-cli.exe`) |
| `claudinho.spec` / `empacotar.py` | o build do PyInstaller e o zip da release |
| `~/.claudinho/config.json` | configurações (movimento, frequência, modos, Meu Mestre, skin, pastas de leitura) |
| `~/.claudinho/CLAUDE.md` | o perfil que o chat lê (gerado a partir do "Meu Mestre" do painel) |
| `memoria.py` | banco SQLite: piadas (com contexto e nota), avisos do dia, conversa; migrações versionadas |
| `~/.claudinho/claudinho.db` | o banco em si (este PC) |

As coisas em `~/.claudinho` são deste PC e não vão pro Git.

## MCP do Claudinho e consultas no YouTube

- **MCP (`claudinho_mcp.py`)**: servidor com duas ferramentas. `abrir_programa(nome)`: abre (ou traz pra frente) qualquer
  programa instalado, pelo nome aproximado ("abre a Steam"), mesmo minimizado ou na bandeja. Não roda comando, não abre
  site, não fecha nada. O chat liga ele sozinho (`~/.claudinho/mcp.json`); a busca dos programas está em `programas.py`.
- **`ver_tela(alvo, janela)`** ("olha a tela e me responde", "que erro é esse?"): o chat tira o print sozinho quando
  você pede, da janela em foco (padrão) ou de um programa pelo nome (`janela="intellij"`, que vem pra frente), do
  monitor ou de todos (`tela.py`, ~1280 px em JPEG). Só lê; o balão mostra "olhando a
  tela…". Respeita a faixa nos olhos e a chave "Olhar a tela quando eu pedir" do painel. Vale no chat digitado e na voz
  (mesmo chat), no motor Claude Code (MCP) e na API (ferramenta `ver_tela` em `motores.py`); o Ollama não tem ferramentas.
- **`atalho(teclas, janela, vezes)` e `atalho_confirmado`** ("vai pra próxima aba", "desce a página", "roda o projeto
  no IntelliJ"): aperta UMA combinação de teclas (nunca texto livre) na janela pedida, trazendo ela pra frente antes
  (`teclas.py`). Três faixas: **livre** (setas, Tab, PageUp/PageDown, Home/End, Esc, F5, Ctrl+Tab, Alt+←/→, Ctrl+F/L/T,
  zoom), **com popup** (o resto: Enter, Delete, Ctrl+S, letras… pela `atalho_confirmado`) e **bloqueada** (Alt+F4,
  Alt+Tab, qualquer coisa com Win, Ctrl+Shift+Esc, Ctrl+Alt+Del). Com a faixa nos olhos, nada de teclas. Só no motor
  Claude Code.
- **`abrir_projeto(programa, projeto)`** ("abre o IntelliJ no LC Pedir API"): acha a pasta do projeto pelo nome só
  dentro das pastas liberadas (`projetos.py`), abre o programa nela e espera o projeto ficar pronto (até 2 min); se já
  estiver aberto, traz pra frente.
- **`esperar_janela(janela)`**: espera sem tempo fixo. Volta assim que a janela apareceu e o programa sossegou (CPU
  baixa por 2 s: IntelliJ abrindo projeto fica em vários núcleos, pronto fica quase parado), e diz quanto levou. O
  chat não pode mais usar `sleep` (bloqueado): PC rápido segue logo, PC lento espera o que precisar. Achou mais de uma pasta (ex.: "LC Pedir" tem _API e _WEB dentro) ou nenhuma: devolve a
  lista e o chat pergunta. O chat faz tarefas com etapas de uma vez: abrir_projeto → atalhos_conhecidos → atalho →
  ver_tela(janela=…) pra conferir; e não fecha programa pra "consertar".
- **Rotinas de sites** (extensão + `rotinas.py`): você ensina mostrando. No navegador, ícone da extensão do Claudinho →
  **Liberar este site** (o navegador pede a permissão só daquele site) → **⏺ Gravar rotina**, faz o caminho (cliques, o
  que digitar, Enter) e, pra ele ler uma lista, **📖 Marcar área pra ler**: o que está sob o mouse fica destacado com o
  número de linhas de texto, **↑** pega a área de fora (do título da coluna até o quadro inteiro), **↓** volta, clique
  escolhe; ou **📄 Ler a página toda**. Na hora de repetir, área que sumiu vira leitura da página toda →
  dá um nome e salva. No chat: "lê meu PlannerX", "consulta o pedido 5678": `rotinas_conhecidas` e `rodar_rotina`
  repetem no seu navegador e devolvem o texto lido, que o chat organiza (tarefas por coluna). No painel (Rotinas de
  sites) dá pra marcar o valor digitado como variável (o chat preenche), marcar passo como "confirmar antes" (popup,
  pela `rodar_rotina_confirmada`), tirar passo, rodar (▶) e apagar. Senha nunca é gravada; o chat só repete o que você
  gravou; site não liberado a extensão nem enxerga. Se o site mudar de layout, ela diz em qual passo parou.
- **Programas** (painel → Programas): tudo o que está instalado (menu Iniciar e Loja), com busca e uma chave por
  programa. Desligado = o Claudinho não abre, não aperta tecla nem olha ele pelo nome (`programas_bloqueados` no
  config). O chat confere o que existe e o nome exato pela `listar_programas` antes de abrir.
- **O que ele abre é seu**: o chat roda num "job" do Windows que fecha junto com o Claudinho (pra não sobrar processo
  dele); programa, site e projeto que ele abre pra você saem do job antes (`sistema.lancar` → `claudinho-cli lancar`),
  então continuam abertos quando o Claudinho fecha ou reinicia.
- **Fechou o balão, ele cala**: fechar a resposta na mão (clique, ✕ ou clique fora) corta a fala também.
- **⏹ Parar**: enquanto ele responde ou faz algo, o balão "digitando/fazendo…" tem o botão **⏹ parar** (e a janela de
  conversa também). Para o chat na hora (Claude Code pelo pedido de interrupção; API e IA local na próxima volta), a
  rotina no navegador no próximo passo e a fala.
- **Nada destrutivo no chat**: fechar processo (taskkill, Stop-Process, kill), apagar (rm, del, Remove-Item), desligar o
  PC ou mexer no registro é recusado sem nem abrir o popup (`PERIGOSO` no `claudinho.pyw`).
- **Atalhos dos programas** (painel → Atalhos): a lista de "o que cada atalho faz" em cada programa, sem programação.
  Escolhe um programa aberto, escreve o que a ação faz, clica em **🎧 Escutar atalho**, aperta as teclas e
  **Adicionar**. Fica no `config.json` (`atalhos_programas`); o chat consulta pela `atalhos_conhecidos` e esses atalhos
  rodam sem confirmação, só na janela daquele programa. Vem de fábrica com o IntelliJ (Shift+F10 roda o projeto,
  Ctrl+F2 para). Atalhos que o próprio navegador não deixa escutar (Ctrl+W, Ctrl+T, Ctrl+N) não dá pra gravar.
- **Consultar sem mexer na tela**: `python musica.py consultar youtube|ytmusic <modo> [termo]` pede pra extensão do
  navegador olhar (pesquisa, início, inscrições, canal, descrição e data de um vídeo; início, biblioteca, curtidas,
  playlists… do YouTube Music) e devolve a lista. **Abrir e levar até lá**: `python musica.py ir youtube|ytmusic <destino>`.

## Próximos passos

- [Plano: contexto de projeto (sessões do Claude Code) pro Júnior](docs/plano-contexto-de-projeto.md): saber em qual projeto o usuário está e conferir no código antes de comentar.
- [Plano: "Minha voz" (Chatterbox direto e Piper treinado)](docs/plano-voz-propria.md): o Claudinho falando com a voz
  que a pessoa mandar (arquivo, vídeo ou link do YouTube), só pra uso pessoal e local.
- [Plano: Claudinho orquestrador + Júnior revisor visual](docs/plano-orquestrador.md): manda a tarefa pro Claude Code do projeto e corrige o que o Júnior achou.
- [Plano: MCP exclusivo do Claudinho](docs/plano-mcp.md): trocar os ajudantes via Bash por um servidor
  MCP com ferramentas próprias (livres e com confirmação).
