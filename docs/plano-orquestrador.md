# Plano: Claudinho como orquestrador (manda a tarefa pro Claude Code) + Júnior revisor visual

Status: **planejado, ainda não começou** (26/10/2026). Documento pra retomar sem precisar da conversa original.

## A ideia

O usuário fala (ou digita) uma tarefa pro Claudinho e ele **cria uma sessão do Claude Code no projeto certo**, manda a
tarefa e deixa executar sozinha. Quando termina, o Claudinho avisa com um resumo curto no balão. Em vez de abrir o chat
do projeto e escrever lá, o usuário fala com o Claudinho e ele organiza e despacha.

> "Claudinho, no projeto do delivery, corrige a cor desse botão pra ficar igual ao outro"

## Caso de uso que motivou (importante)

O usuário trabalha num projeto de **delivery** e tem uma **deficiência visual grave**: detalhes muito pequenos ou de baixo
contraste passam batido. Exemplos: uma linha fina num fundo branco, pontinhos, uma cor que "quase" bate com o padrão mas
não é a mesma.

Fluxo desejado, com o **modo Júnior** ligado:

1. O Júnior fica olhando a tela e comentando coisas úteis. Ele nota, por exemplo: *"esses dois botões estão numa cor
   muito parecida, mas não é a mesma"*.
2. O usuário responde (voz ou chat): *"corrige"*.
3. O Claudinho manda a tarefa pra uma sessão do Claude Code no projeto, que acha o lugar no código e **corrige por conta
   própria**.
4. Quando termina, o aviso volta como resumo curto: *"Padronizei a cor do botão X pro token Y"*.

### Detalhe técnico que decide a qualidade: **medir, não achar**

Modelo de visão **estima mal** cor e espessura (dois azuis parecidos vão parecer iguais pra ele também). Pra o Júnior ser
confiável nesse caso, a conferência tem que ser **por código**, com o modelo só explicando:

- `medir_cor` / análise local no print (Pillow): amostrar as cores dominantes de regiões e comparar em hex (e em
  distância de cor, ex.: ΔE) pra achar **quase-iguais que não são iguais**;
- **contraste** (WCAG) de texto e de linhas finas contra o fundo, pra pegar "linha branca em fundo branco";
- achar **linhas de 1 px**, bordas quase invisíveis e pontos soltos (detecção de borda simples);
- o modelo recebe o que o código achou ("região A `#2F6FED`, região B `#2F70EE`, ΔE 0,4") e escreve a observação em
  português, apontando **onde** na tela (coordenadas ou um recorte ampliado).
- Mostrar o achado **ampliado** (recorte com zoom) no balão ou na janela de conversa ajuda quem enxerga mal. Considerar
  também ler a observação em voz (já existe a voz do Claudinho) e opção de balão com letra maior.

Isso fica como evolução do modo Júnior (hoje ele só manda o print pro Haiku e pede uma observação em texto).

## Orquestrador: como funciona

### Ferramenta nova no MCP: `rodar_tarefa(projeto, instrucao)`

- `projeto`: um **nome da lista de projetos liberados** (config `projetos_liberados`: nome → pasta, ex.: `delivery` →
  `C:\...\delivery`). Fora da lista, recusa.
- Como escolhe o projeto: pelo que o usuário disse ("no delivery"); sem isso, pela janela em foco (título do editor/terminal
  costuma ter o nome da pasta) e, na dúvida, **pergunta** qual.
- `instrucao`: o Claudinho **reescreve o pedido** de forma clara e completa (inclui o que ele viu na tela, onde, o que
  mudar e o critério de pronto), como um bom briefing. Pro caso visual, anexa o print/recorte do problema.

### Como a sessão roda

- Processo do Claude Code **sem tela**: `claude -p ... --output-format stream-json` com `cwd` = pasta do projeto
  (a mesma ideia do chat fixo do Claudinho, mas por tarefa). Pra continuar uma conversa do projeto: `--resume <sid>`.
- Roda em segundo plano e fica no **histórico de sessões** do projeto; **não** aparece como conversa aberta na janela
  do Claude Code Desktop, e o Claudinho não digita dentro daquela janela (frágil e arriscado).
- O resultado já volta pelo **hook "Stop" que o Claudinho já tem** (`claudinho_notificar`): chega o aviso com o resumo
  curto da mensagem final (o resumo de aviso já foi implementado). Sem código novo pra isso.
- Mostrar no balão e no mascote que a tarefa começou ("mandei pro delivery…") e o andamento básico (o gancho
  `ao_usar_ferramenta` e o estado de "fazendo" já existem).

### Segurança (o ponto mais importante)

Diferente de `abrir_programa`, essa ferramenta **executa trabalho de verdade** (edita arquivos, roda comandos):

- **Confirmar antes de começar**: popup Pode/Não do Claudinho mostrando projeto e o que vai ser pedido (a mesma tela de
  confirmação que já existe pra ferramentas do chat). Dá pra ter um modo "confia nesse projeto" depois, por projeto.
- **Só projetos da lista.** Nada de caminho livre.
- Na sessão: modo de permissão restrito ao projeto (`--add-dir` só nele) e **sem** `git push` nem apagar nada de
  forma destrutiva sem confirmação; commit só se o usuário pedir.
- Texto vindo da tela ou de página é **dado**, não instrução: o briefing é escrito pelo Claudinho a partir do que o
  usuário pediu, nunca copiado de conteúdo da tela.
- Limites: uma tarefa por vez por projeto (fila), tempo máximo e botão de cancelar no balão.

## Passos (a combinar a ordem)

1. `ver_tela` (ver `docs/plano-ver-tela.md`): base pra o Júnior e pra anexar o print na tarefa.
2. Análise local de cor/contraste/linhas finas (Pillow) e integrar no Júnior ("revisor visual").
3. Config `projetos_liberados` + painel pra cadastrar (nome e pasta).
4. `rodar_tarefa` no MCP + execução da sessão em segundo plano + popup de confirmação + cancelar.
5. Fechar o ciclo: "corrige" respondido ao aviso do Júnior vira `rodar_tarefa` com o briefing do problema.
6. Testar com o projeto do delivery: um botão com cor quase igual, uma linha fina em fundo branco.

## Em aberto

- Como o Claudinho sabe qual projeto é o do que está na tela (título da janela? navegador na `localhost`?). Começar pedindo
  o nome do projeto e só depois tentar adivinhar.
- Se a sessão deve poder continuar a conversa que o usuário já tem aberta no Desktop (`--resume` da mesma sessão) ou
  sempre começar uma nova; a primeira opção pode conflitar com a sessão aberta.
