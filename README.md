# Claudinho

Mascote de mesa em pixel art que vive na tela do Windows, feito em Python. Ele passeia, corre entre
monitores atrás do mouse, conversa com você usando o Claude Code, avisa quando seus chats do Claude Code
terminam e solta piadas sobre o que está na tela.

## O que ele faz

- **Chat rápido:** clique nele e pergunte. A resposta vem num balão com o campo pra continuar a conversa.
  Usa o Claude Code instalado no PC (Haiku com pensamento leve), com a sua memória e o seu perfil.
- **Mexe no PC com confirmação:** abre site, pesquisa ou programa da lista sem perguntar (via `abrir.py`);
  qualquer outro comando ou mudança em arquivo pede **Pode / Não** num balão.
- **Avisos em fila:** quando um chat do Claude Code termina, ele avisa (projeto, o que foi pedido, resposta).
  Sua pergunta tem prioridade; os avisos esperam e somem sozinhos.
- **Piadas sobre a tela:** banco de frases + Haiku olhando um print. Modos maldoso 😈 e TDAH 🐿️,
  avaliação boa/ruim (ele aprende), memória do dia e **faixa nos olhos 🙈** (aí não tira print).
- **Sprites:** andando, correndo entre monitores, notebook digitando, pensando, sendo carregado, vendado.
- **Atalho:** `Win+Y` comenta a tela na hora. Menu no botão direito e no ícone da bandeja.

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
| `hook/claudinho_notificar.py` | hook "Stop" do Claude Code que manda os avisos |
| `instalar.py` | instalação num PC novo |
| `~/.claudinho/config.json` | configurações (movimento, frequência, modos, atalho, pastas de leitura) |
| `~/.claudinho/CLAUDE.md` | seu perfil |
| `~/.claudinho/estado.json`, `avaliacoes.json` | conversa, memória do dia, piadas recentes, notas |

As coisas em `~/.claudinho` são deste PC e não vão pro Git.
