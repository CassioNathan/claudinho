# Claudinho

Mascote de mesa em pixel art que vive na tela do Windows, feito em Python. Ele passeia, corre entre
monitores atrás do mouse, conversa com você usando o Claude Code, avisa quando seus chats do Claude Code
terminam e solta piadas sobre o que está na tela.

## O que ele faz

- **Chat rápido:** clique nele e pergunte. A resposta vem num balão com o campo pra continuar a conversa.
  Ele lembra do que acabou de falar nos balões: clicou logo depois de uma piada ou aviso, a conversa
  abre nela e dá pra responder direto ("ué, por que pão de queijo?").
  Usa o Claude Code instalado no PC (Haiku com pensamento leve), com a sua memória e o seu perfil.
- **Mexe no PC com confirmação:** abre site, pesquisa ou programa da lista sem perguntar (via `abrir.py`);
  qualquer outro comando ou mudança em arquivo pede **Pode / Não** num balão.
- **Avisos em fila:** quando um chat do Claude Code termina, ele avisa (projeto, o que foi pedido, resposta).
  Sua pergunta tem prioridade; os avisos esperam e somem sozinhos.
- **Piadas sobre a tela:** banco de frases + Haiku olhando um print. Modos maldoso 😈 e TDAH 🐿️,
  avaliação boa/ruim (ele aprende), memória do dia e **faixa nos olhos 🙈** (aí não tira print).
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
- **Skins:** uma cor (10, incluindo arco-íris) e um adereço por espaço (cabeça, olhos, rosto, pescoço, braços),
  28 adereços e 9 pacotes prontos (emo, CEO, natal, cowboy, pirata, anjinho, diabinho, gamer, rei).
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
- **Personalidade 🤖:** no painel, "Claudinho" ou "Ultron" (IA vilã teatral, frases próprias): muda o tom das piadas
  do Haiku, o banco de frases e o jeito de falar no chat (que continua ajudando de verdade; vai nas instruções fixas
  do chat, sem custo por mensagem). Combina com a cor Metal de olhos vermelhos / pacote Ultron.
- **Autoconfiança 😎:** ele sabe como está (cor, adereços, emo, venda) e onde aparece no print. De vez em quando a
  piada é ele se gabando (no Haiku e no banco de frases), comenta quando você troca a roupa dele, e se aparecer o
  logo do Claude/Claude Code na tela ele reage ("esse sou eu", "meu irmão gêmeo", "isso é um espelho?").
- **Mini cérebro 🧠:** cada aviso do Claude Code (pedido + resultado) e cada troca do chat viram lembrança no
  SQLite, com busca de texto local (FTS5). Ao perguntar algo parecido com o que já rolou, até 3 lembranças curtas
  (~250 tokens) vão junto; sem nada parecido, não vai nada. Guardar e buscar não usa IA nenhuma. Liga/desliga no painel.
- **Formatação:** os balões convertem o markdown das respostas (tabela vira lista, títulos, negrito, crases e links somem).
- **Prioridade das falas:** aviso, coisa que você pediu e erro nunca são atropelados (nem enquanto você lê);
  piada sai da frente pra eles; mensagem de estado (vendei, modo ligado…) é descartável e é trocada na hora. Liga/desliga no menu; "Esquete agora 🎭" roda uma na hora.
  Pra testar uma específica: `CLAUDINHO_ESQUETE=inseto` antes de abrir.
- **Emo no rock 🖤:** começou uma música de rock, ele vira emo uns 45 s (franja, mecha rosa,
  munhequeira, headbang) e solta um desabafo. Quem decide se é rock é o Haiku, uma vez por artista (fica guardado).
- **Conversa:** no balão dá pra anexar um print (aparece uma miniatura dele) da janela que você está usando e abrir
  "ver conversa" com o histórico inteiro. Notificação ou outro programa pulando na frente não fecha
  a conversa; só clicar fora.

## Instalar (quem só quer usar)

Baixe o `Claudinho-<versão>-windows.zip` em **Releases**, descompacte onde quiser e abra o `Claudinho.exe`.
Não precisa de Python. Na primeira vez ele abre o painel: conte quem você é em **Meu Mestre** e, se quiser,
ligue em **Sistema** "abrir junto com o Windows" e o aviso do Claude Code.

- O chat, as piadas olhando a tela e os resumos usam o [Claude Code](https://claude.com/claude-code)
  (instale, rode `claude` e faça `/login`). Sem ele, o resto funciona: banco de frases, música, esquetes, skins.
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

## Próximos passos

- [Plano: MCP exclusivo do Claudinho](docs/plano-mcp.md): trocar os ajudantes via Bash por um servidor
  MCP com ferramentas próprias (livres e com confirmação).
