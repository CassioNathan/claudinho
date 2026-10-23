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
  Menu no botão direito e no ícone da bandeja.
- **Esquetes (à toa):** de vez em quando, parado, ele apronta: "Tive uma ideia!", saca o notebook,
  trabalha e conta o resultado (às vezes um app novo, às vezes "acabaram meus tokens"); deploy do nada,
  git push --force suando, café, cochilo, alongamento, dancinha, caça ao bug (aparece uma joaninha,
  ele vai lá e come: "Removi um bug 😄"), build quebrado com nuvem de chuva, servidor pegando fogo,
  patinho de borracha, npm install que vira caixa gigante, pizza (só de noite), joguinho, faxina de
  código morto, reunião que podia ser e-mail, bug que vira borboleta e malhação. Às vezes uma esquete
  entra no lugar de uma piada. Liga/desliga no menu; "Esquete agora 🎭" roda uma na hora.
  Pra testar uma específica: `CLAUDINHO_ESQUETE=inseto` antes de abrir.
- **Emo no rock 🖤:** começou uma música de rock, ele vira emo uns 45 s (franja, mecha rosa,
  munhequeira, headbang) e solta um desabafo. Quem decide se é rock é o Haiku, uma vez por artista (fica guardado).
- **Conversa:** no balão dá pra anexar um print (aparece uma miniatura dele) da janela que você está usando e abrir
  "ver conversa" com o histórico inteiro. Notificação ou outro programa pulando na frente não fecha
  a conversa; só clicar fora.

## Instalar num PC novo

Precisa de: Windows, Python 3.11+ e o [Claude Code](https://claude.com/claude-code) instalado.

```bash
git clone https://github.com/CassioNathan/claudinho.git
cd claudinho
python instalar.py --iniciar
```

O instalador:
1. instala as dependências;
2. registra o hook de aviso no `~/.claude/settings.json`, com backup;
3. cria o seu perfil em `~/.claudinho/CLAUDE.md`;
4. com `--iniciar`, faz ele abrir junto com o Windows.

Depois:
1. Logue o Claude Code: rode `claude` no terminal e digite `/login` (conta com assinatura).
2. Abra o Claudinho: duplo clique em `claudinho.pyw`.
3. Edite `~/.claudinho/CLAUDE.md` contando quem você é. Ele usa isso no chat e nas piadas.

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
| `instalar.py` | instalação num PC novo |
| `~/.claudinho/config.json` | configurações (movimento, frequência, modos, atalho, pastas de leitura) |
| `~/.claudinho/CLAUDE.md` | seu perfil |
| `memoria.py` | banco SQLite: piadas (com contexto e nota), avisos do dia, conversa; migrações versionadas |
| `~/.claudinho/claudinho.db` | o banco em si (este PC) |

As coisas em `~/.claudinho` são deste PC e não vão pro Git.

## Próximos passos

- [Plano: MCP exclusivo do Claudinho](docs/plano-mcp.md): trocar os ajudantes via Bash por um servidor
  MCP com ferramentas próprias (livres e com confirmação).
