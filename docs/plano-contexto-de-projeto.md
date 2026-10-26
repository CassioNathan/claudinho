# Plano: o Claudinho saber em qual projeto/sessão do Claude Code o usuário está (e usar isso no modo Júnior)

Status: **planejado, ainda não começou** (26/10/2026). Documento pra retomar sem precisar da conversa original.

## A ideia

Ele já viu (no projeto antigo "Claudecímetro") que dá pra saber **qual sessão do Claude Code está ativa** e quanto ela
gasta. Trazendo isso pro Claudinho:

- No modo **Júnior**, ele nota sozinho em qual **projeto** o usuário está mexendo e **pergunta uma vez** se pode olhar o
  código dele também ("Vi que você está no `delivery`. Posso olhar o código desse projeto pra te ajudar melhor?").
- Com o projeto conhecido, ele **olha o código antes de falar**: em vez de só achar pelo print que dois botões têm cores
  "parecidas", ele procura no código (CSS, tokens de cor, componentes) e confirma ("o botão A usa `#2F6FED` e o B,
  `#2F70EE`, em `botoes.css`"). Isso resolve a fraqueza do modelo de visão com cor, linha fina e botão (ver
  `docs/plano-orquestrador.md`) e deixa a sugestão de correção bem mais certeira.
- Com o projeto na mão, o orquestrador (`rodar_tarefa`) já sabe pra qual pasta mandar a tarefa, sem perguntar.

## O que a gente descobriu (verificado neste PC, Claude Code 2.1.308)

### 1. Registro de sessões ao vivo: `~/.claude/sessions/<pid>.json`

Cada processo do Claude Code em execução grava um arquivinho (atualizado enquanto roda) com:

| Campo | Pra que serve |
|---|---|
| `sessionId` | liga com o transcript da sessão (abaixo) |
| `cwd` | **a pasta do projeto** |
| `name` | o título da conversa (ex.: "Stompdesk pythonnet runtime error") |
| `status` | `busy` (trabalhando) ou `idle` (esperando você) |
| `updatedAt`, `statusUpdatedAt`, `startedAt` | milissegundos desde 1970; dá pra saber a mais recente |
| `entrypoint` | `claude-desktop`, `sdk-cli`... (o chat do próprio Claudinho aparece como `sdk-cli`, em `~/.claudinho`) |
| `kind`, `pid`, `version`, `hostSessionId` | detalhes |

Vê-se aqui, por exemplo, uma sessão do Stompdesk (`idle`) e esta do Claudinho (`busy`) abertas ao mesmo tempo.

### 2. Gasto de tokens: o transcript `~/.claude/projects/<pasta-codificada>/<sessionId>.jsonl`

Cada resposta do assistente tem `message.usage` com `input_tokens`, `output_tokens`, `cache_read_input_tokens` e
`cache_creation_input_tokens`. Somando dá o gasto da sessão (é a base do que o Claudecímetro fazia).

### 3. O que **não** existe: um campo "esta é a sessão em foco"

Nenhum dos arquivos diz qual conversa está na frente do usuário. Dá pra **deduzir** combinando sinais (do mais forte ao mais fraco):

1. a janela em foco (`janelas.janela_ativa()`): o título do Claude Code Desktop costuma trazer o nome da conversa, e o de
   editor/terminal/navegador (localhost) traz o nome da pasta do projeto, que bate com o `cwd`/`name` de alguma sessão;
2. a sessão `busy` (está trabalhando agora);
3. a de `updatedAt` mais recente.

Na dúvida (duas sessões plausíveis) ele pergunta, em vez de adivinhar.

> **Claudecímetro:** o projeto antigo **não está neste PC** (em `Projetos` só tem `claudinho` e `Stompdesk`). Se ele estiver em
> outro lugar (outro PC, GitHub), vale trazer o código dele de lá pra reaproveitar o que já funciona.
> Ressalva: esse registro de sessões é um formato **interno e não documentado** do Claude Code; pode mudar entre versões,
> então o código tem que ser tolerante (campo faltando = ignora, nunca quebra).

## Desenho

### Módulo novo `sessoes.py`

- `listar()`: lê `~/.claude/sessions/*.json`, descarta as de processo morto (o `pid` não existe mais) e devolve
  `[{sessao, pasta, projeto, nome, status, atualizada, entrypoint}]`. `projeto` = nome da pasta.
- `em_foco()`: o palpite acima (devolve a sessão e o quanto tem de certeza).
- `uso(sessao)`: soma os tokens do transcript (lendo só o que é novo desde a última vez, pra ser barato).
- Tudo local, só leitura. Nada disso sai do PC.

### Modo Júnior com contexto de projeto

- A cada olhada, `contexto` do prompt ganha uma linha: "Projeto em que ele está: delivery (pasta …), sessão '…'".
- **Consentimento por projeto** (uma vez): "posso olhar o código do `delivery`?". Sim guarda em
  `projetos_liberados` (a mesma lista do orquestrador); não guarda "não perguntar de novo". Painel pra rever e remover.
- **Conferir no código antes de falar** (só projeto liberado, só leitura): quando o print sugere um achado visual, uma sessão
  curta e **somente leitura** do Claude Code (`Read`, `Glob`, `Grep`, `--add-dir` na pasta, Haiku) acha o que
  corresponde no código e confirma o número (cor em hex, espessura, classe). O balão traz o achado já com o arquivo
  e a linha. Se o código não confirmar o que o print sugeriu, ele **não comenta** (menos falso alarme).
- Latência: roda em segundo plano e só fala quando confirma; o Júnior já fala de tempos em tempos, não em tempo real.

### Extras baratos que saem do mesmo módulo

- Gasto de tokens da sessão atual no painel ou numa frase ("essa conversa já gastou ~X mil tokens"), como o Claudecímetro.
- O balão de aviso de "chat terminou" já mostra o projeto; com isso dá pra mostrar também o gasto.

## Segurança e privacidade

- Ler `~/.claude/sessions` e os transcripts é local. O conteúdo do transcript **não** vai pra IA do Júnior; só metadados
  (nome do projeto, pasta, status) e, depois do consentimento, o que a sessão de leitura achar no código.
- Sessão de leitura sem `Write`/`Edit`/`Bash`: não altera nada. Corrigir é outro passo (`rodar_tarefa`, com confirmação).
- Projeto só entra na lista com o "sim" do usuário.

## Passos

1. `sessoes.py` (`listar`, `em_foco`, `uso`) com testes em cima dos arquivos reais; palpite de foco validado com 2 sessões abertas.
2. Linha de projeto no contexto do Júnior; teste: abrir o `delivery` e ver o comentário citar o projeto.
3. Pergunta de consentimento + lista `projetos_liberados` no painel (compartilhada com o orquestrador).
4. Sessão de leitura pra conferir achado no código; teste com dois botões de cor quase igual.
5. (Opcional) gasto de tokens da sessão no painel; trazer o código do Claudecímetro se estiver em outro lugar.

## Em aberto

- Onde está o código do Claudecímetro (outro PC? GitHub?).
- Como o título da janela do Claude Code Desktop identifica a conversa (precisa conferir com uma sessão aberta e a
  janela em foco).
- Navegador em `localhost`: como ligar a aba do app (delivery) à pasta do projeto, já que o título da aba não traz a pasta.
