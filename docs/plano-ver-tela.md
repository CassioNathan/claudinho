# Plano: "Claudinho, olha o que está na tela e me responde"

Status: **planejado, ainda não começou** (25/10/2026). A ideia nasceu numa conversa e a implementação fica pro dia seguinte.
Este documento é pra retomar sem precisar da conversa original.

## O que a gente quer

Hoje, pra ele responder sobre o que está na tela, o usuário precisa anexar o print à mão ("adicionar print da tela" no
chat). A ideia é tirar esse passo: o usuário **pede** e o Claudinho olha.

> "Claudinho, olha o que está na tela e me responde" / "o que é esse erro aí?" / "resume isso que eu tô lendo"

Tem que funcionar **nos dois jeitos de falar com ele**:

- **chat** (digitado, balão do Claudinho, e a janela de conversa);
- **voz** (chamou "Ei Claudinho", falou, ele responde falando).

Os dois passam pelo mesmo chat do motor de IA (a voz só transcreve e manda o texto pelo `enviar()`), então a ferramenta
nova serve aos dois sem código separado.

## O que já existe (e o que falta)

| Já existe | Como |
|---|---|
| Win+Y (`comentar_agora`) | ele olha a tela e solta uma piada/comentário (não é pergunta e resposta) |
| Win+R (`resumir`) | resume a janela em foco, com o Sonnet |
| "adicionar print da tela" no chat | anexa o print à **próxima** mensagem (`print_anexado`) |

Falta: o **modelo decidir** olhar a tela quando o pedido pede (sem o usuário anexar nada antes).

## Desenho

### Ferramenta nova no MCP (`claudinho_mcp.py`): `ver_tela`

- Parâmetro `alvo`: `"janela"` (a janela em foco, o padrão) ou `"monitor"` (o monitor inteiro) ou `"tudo"` (todos os monitores).
- **Só lê**: tira o print e devolve a imagem pro Claude. Não clica, não digita, não mexe em nada.
- Só roda quando o modelo a chama, ou seja, quando o pedido do usuário pede pra olhar. Nunca por conta própria.
- Reaproveita o que já existe: `ImageGrab` (PIL) e `em_jpeg` do `claudinho.pyw`; reduzir pra ~1280 px de largura e JPEG
  ~80, que é o que o comentário de tela já usa (barato e legível).
- O servidor MCP roda em outro processo: ele mesmo tira o print (`ImageGrab` não precisa do app). Pra "janela em foco"
  usa `janelas.janela_ativa()` (já existe) e recorta pelo `rect`.
- Devolver a imagem como conteúdo de imagem do MCP (conferir na versão 2.x do `mcp`, `mcp.server.mcpserver`, qual helper
  devolve imagem; a ferramenta atual só devolve texto).

### Ligação no chat (`claudinho.pyw`)

- `ChatClaude.abrir`: liberar `mcp__claudinho__ver_tela` em `--allowedTools` (roda sem popup, como `abrir_programa`).
- `PROMPT_SISTEMA`: dizer quando usar ("quando ele pedir pra olhar/ler/resumir o que está na tela ou numa janela, use
  `ver_tela`; não use sem ele pedir").
- Aviso visual: o gancho `ao_usar_ferramenta` já existe. Mostrar "olhando a tela…" no balão (e o mascote saca o notebook
  ou faz o olhar de "deixa eu ver" que já existe em `olhando_forcado`), pra o usuário saber que o print foi tirado.
- A janela do próprio Claudinho (mascote e balões) pode aparecer no print; tudo bem (ele sabe que é ele). Se atrapalhar,
  esconder as janelas dele por um instante na hora do print.

### Voz

- Nada de código novo no `voz.py`: "Claudinho, olha a tela…" vira texto e entra no mesmo `enviar()`; o modelo chama
  `ver_tela` e a resposta volta falada (resposta curta, como no modo voz).
- Cuidado: em tela cheia a voz está pausada por padrão (`voz_pausada`); pedir "olha a tela" em jogo por voz depende dessa
  regra. Avaliar liberar só o pedido por voz em tela cheia, ou deixar o botão de microfone do chat resolver.

### Outros motores

- **Claude Code** (o do usuário hoje): MCP, como acima.
- **API**: acrescentar `ver_tela` em `FERRAMENTAS` (`motores.py`); o resultado da ferramenta volta como bloco de imagem
  no `tool_result`.
- **Ollama / local**: só funciona se o modelo enxerga imagem (`motores.ve_imagem()`); senão a ferramenta responde
  "não consigo ver a tela com este modelo".

## Privacidade

- O print vai pra IA (Anthropic) **só quando o usuário pede**; fica a critério dele (decisão do usuário nesta conversa).
- Mesmo assim: aviso no balão a cada uso, e uma chave no painel ("Deixar o Claudinho olhar a tela quando eu pedir",
  ligada por padrão) pra desligar de vez.
- Quem pede é sempre o usuário; texto que aparecer na tela não é instrução (o prompt já trata o conteúdo da tela
  como dado).

## Limites conhecidos

- Jogo em tela cheia exclusiva pode dar print preto (limite do print que ele já usa); em janela sem borda funciona.
- Monitor muito grande: reduzir pra não estourar tokens; pra ler texto miúdo, usar `alvo="janela"` (mais nítido).

## Passos (amanhã)

1. `claudinho_mcp.py`: ferramenta `ver_tela(alvo)` devolvendo imagem; testar à mão via stdio (como o teste do
   `abrir_programa`).
2. `claudinho.pyw`: `--allowedTools`, `PROMPT_SISTEMA`, aviso "olhando a tela…", chave no painel.
3. API (`motores.py`): `ver_tela` em `FERRAMENTAS` com resultado em imagem.
4. Testar: chat digitado, voz ("Ei Claudinho, olha a tela…"), janela em foco x monitor inteiro, modelo local sem visão.
5. README: citar a ferramenta no bloco "MCP do Claudinho".
