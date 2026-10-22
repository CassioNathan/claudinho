# Plano: MCP exclusivo do Claudinho

Status: **planejado, ainda não começou** (22/10/2026). Este documento é pra continuar o trabalho em
outro PC/sessão sem precisar da conversa original.

## Por quê

Hoje o chat do Claudinho age no PC assim:

- roda com a ferramenta **Bash** liberada;
- dois ajudantes limitados (`abrir.py` e `musica.py`) passam **sem confirmação** porque o comando
  bate numa regex (`AJUDANTE` em `claudinho.pyw`) e numa regra `--allowedTools "Bash(python abrir.py:*)"`;
- tentativas de abrir coisa "na mão" (`start`, `Start-Process`, `explorer`) são recusadas sem popup
  e redirecionadas pros ajudantes (`ABRIR_NA_MAO`);
- todo o resto (outros comandos, criar/editar arquivo) pede **Pode/Não** num balão
  (`--permission-prompt-tool stdio` → `ChatClaude.responder_controle` → `pedir_permissao`).

Funciona, mas é frágil: o Haiku às vezes ignora o ajudante (já abriu o YouTube pelo `cmd`), a
liberação depende de regex em cima de texto de comando, e o Bash continua disponível pra qualquer coisa.

Um **servidor MCP só do Claudinho** troca isso por ferramentas de verdade, com nome e parâmetros.

**O MCP muda a organização, não a segurança:** o que decide se é seguro é o que cada ferramenta faz.

## Ganhos

- **Ferramentas tipadas** (`abrir_site(url)`, `musica(acao)`) em vez de "rode `python abrir.py ...` no Bash":
  o modelo erra bem menos.
- **Permissão por ferramenta**: `--allowedTools mcp__claudinho__abrir_site` libera direto; o resto cai
  no popup que já existe. Sem regex em cima de comando.
- **Tirar o Bash do chat** (`--tools ""` ou não listar Bash): "rodar comando qualquer" deixa de existir.
- **O mascote reage a cada ferramenta** (já existe o gancho `ao_usar_ferramenta`): notebook, emoji ⚡,
  balão "abrindo o Spotify…".
- `abrir.py` e `musica.py` viram ferramentas do mesmo servidor (um lugar só).

## Ferramentas propostas

### Livres (sem confirmação)
| Ferramenta | O que faz | Reaproveita |
|---|---|---|
| `abrir_site(url)` | só http(s); completa `https://` | `abrir.abrir_site` |
| `pesquisar(termo, buscador)` | google/youtube/bing/duckduckgo | `abrir.py` |
| `abrir_programa(nome)` | só da lista `programas_liberados` | `abrir.abrir_programa` |
| `musica(acao)` | tocando/pausar/tocar/alternar/proxima/anterior | `musica.py` |
| `volume(nivel)` / `mudo(bool)` | volume do sistema | novo (pycaw ou WinRT) |
| `focar_janela(nome)` / `minimizar_janela(nome)` | por programa/título | `janelas.py` + `abrir.forcar_frente` |
| `lembrete(minutos, texto)` | o Claudinho avisa depois | fila de falas do mascote |
| `modo_foco(ligado)` | venda + silencia piadas | `cfg["vendado"]`, `comentar_tela` |

### Com confirmação (popup Pode/Não)
| Ferramenta | Por quê confirmar |
|---|---|
| `fechar_programa(nome)` | pode perder trabalho não salvo |
| `copiar(texto)` (área de transferência) | sobrescreve o que você copiou |
| `rodar_script(nome)` | só scripts de uma lista sua, mas executam coisas |
| `criar_arquivo(caminho, conteudo)` | escreve no disco |

### Fora (não fazer)
- **clique livre** `clicar(x, y)` e **digitação livre** `digitar(texto)`: genéricos demais. A IA decide
  tudo e um texto na tela/página pode tentar mandar nela (prompt injection). Se precisar, criar
  **ações específicas** ("pausar o vídeo", "próxima aba", "colar na janela X") que só fazem aquilo.
- apagar arquivos, mandar mensagens (WhatsApp/Discord/e-mail), qualquer coisa de dinheiro.
- O **Windows-MCP** já instalado é do tipo genérico (clicar/digitar): não usar no Claudinho sem
  confirmação a cada ação.

## Como implementar (passos)

1. `pip install mcp` (SDK oficial) e adicionar em `requirements.txt`.
2. Criar `claudinho_mcp.py` com `FastMCP("claudinho")`; cada ferramenta é uma função com `@mcp.tool()`,
   reaproveitando `abrir.py`, `musica.py` e `janelas.py`. Transporte stdio.
3. No `ChatClaude.abrir` (`claudinho.pyw`):
   - gerar um `mcp.json` em `~/.claudinho` apontando pro `claudinho_mcp.py` (com o python atual);
   - trocar `--strict-mcp-config` por `--strict-mcp-config --mcp-config <mcp.json>`;
   - `--allowedTools` com as ferramentas livres (`mcp__claudinho__abrir_site`, ...);
   - tirar `Bash` das ferramentas do chat; remover `AJUDANTE`/`ABRIR_NA_MAO` e as regras de Bash.
4. `PROMPT_SISTEMA`: trocar as instruções de `python abrir.py ...` pela lista de ferramentas.
5. `descrever_acao`: textos amigáveis pras ferramentas com confirmação.
6. Lembrete e modo foco precisam falar com o mascote: o servidor MCP roda em outro processo, então
   mandar pro servidor HTTP local do Claudinho (porta 47821, hoje só `/aviso`): criar `/lembrete` e `/foco`.
7. Testar uma ferramenta por vez (como foi feito com o `abrir.py`: recusa o que não pode, passa o que pode,
   popup no resto) e só então apagar `abrir.py`/`musica.py` do fluxo do chat (podem continuar como módulos).
8. Atualizar `README.md` e `instalar.py` (dependência nova).

## Onde mexer hoje (referência rápida)

- `claudinho.pyw` → `ChatClaude` (processo do chat, flags, `responder_controle`), `AJUDANTE`,
  `ABRIR_NA_MAO`, `PROMPT_SISTEMA`, `pedir_permissao`/`mostrar_permissao`, `descrever_acao`.
- `abrir.py` → abrir site/pesquisa/programa + trazer janela pra frente (`forcar_frente`).
- `musica.py` → controles de mídia do Windows (WinRT).
- `janelas.py` → listar janelas, janela ativa.
