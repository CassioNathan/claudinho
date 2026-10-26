# Graph Report - claudinho  (2026-10-26)

## Corpus Check
- 35 files · ~70,943 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 2, .spec 1)

## Summary
- 1035 nodes · 2117 edges · 55 communities (33 shown, 22 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 67 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f19f5edb`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- fala.py · stt.py
- musica.py · notificacoes.py
- carregar() polling /api/estado
- frases.py · esquetes.py
- Balao
- Claudinho
- memoria.py · Memoria
- programas.py
- subprocess
- .comentar_do_banco
- teclas.py
- voz.py
- plano-mcp.md · plano-orquestrador.md
- claudinho.pyw · comentários
- claudinho.pyw · ChatClaude
- .talvez_comentar_musica
- consultas.js
- Voz
- skins.py
- .transcrever_detalhado
- .__init__
- sistema.py · instalar.py
- motores.py · chats
- janelas.py
- .soltar_emoji
- .estado_painel
- claudinho.pyw · servidor
- manifest.json
- fundo.js
- normalizar
- ._ouvir_turno
- iniciar_atalho
- .resumir_tela
- chave_da_extensao
- conversa.html
- plano-ver-tela.md
- icone_enviar
- normalizar
- claudinho_notificar.py
- escrever_perfil
- tela_cheia
- motores.py
- claudinho.pyw · Gravador
- ytmusic.js
- _criar_job
- entrada
- README.md · painel
- plano-ver-tela.md · atalhos
- plano-ver-tela.md · resumir
- painel.html · modo jogo
- README.md · autoconfiança
- README.md · chat rápido

## God Nodes (most connected - your core abstractions)
1. `Claudinho` - 134 edges
2. `Memoria` - 30 edges
3. `Voz` - 30 edges
4. `Balao` - 25 edges
5. `Fala` - 17 edges
6. `main()` - 16 edges
7. `ChatClaude` - 14 edges
8. `listar()` - 14 edges
9. `ChatSimples` - 12 edges
10. `abrir()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `trabalho()` --calls--> `tocar_no_youtube_music()`  [EXTRACTED]
  claudinho.pyw → musica.py
- `Plano: contexto de projeto (sessões do Claude Code) pro Júnior` --references--> `Modo Júnior (config modo_junior)`  [INFERRED]
  docs/plano-contexto-de-projeto.md → painel.html
- `ver_tela(alvo) ferramenta MCP` --conceptually_related_to--> `Faixa nos olhos (vendado)`  [INFERRED]
  docs/plano-ver-tela.md → README.md
- `carregar_config()` --calls--> `configurar()`  [EXTRACTED]
  claudinho.pyw → motores.py
- `carregar_config()` --calls--> `visual_valido()`  [EXTRACTED]
  claudinho.pyw → skins.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Páginas HTML que falam com a API local do Claudinho via X-Token** — conversa_atualizar, painel_api, conversa_x_token, conversa_api_conversa, painel_api_estado [INFERRED 0.85]
- **Ferramentas do servidor MCP do Claudinho** — claudinho_mcp, readme_mcp_do_claudinho, docs_plano_mcp_ferramentas_livres, docs_plano_mcp_ferramentas_com_confirmacao, docs_plano_ver_tela_ver_tela, docs_plano_orquestrador_rodar_tarefa [INFERRED 0.85]
- **Júnior vê, confere no código e despacha correção pro Claude Code** — painel_modo_junior, docs_plano_ver_tela_ver_tela, docs_plano_orquestrador_medir_cor, docs_plano_contexto_de_projeto_conferir_no_codigo, docs_plano_orquestrador_rodar_tarefa, docs_plano_orquestrador_projetos_liberados [INFERRED 0.85]

## Communities (55 total, 22 thin omitted)

### Community 0 - "fala.py · stt.py"
Cohesion: 0.05
Nodes (19): testar(), catalogo(), dividir_em_frases(), efeito_anime(), efeito_ultron(), eh_edge(), eh_kokoro(), Fala (+11 more)

### Community 1 - "musica.py · notificacoes.py"
Cohesion: 0.06
Nodes (31): trabalho(), resumir_notificacoes(), abrir_aba_nova(), assistir(), buscar(), consultar(), consultar_ext(), controlar() (+23 more)

### Community 2 - "carregar() polling /api/estado"
Cohesion: 0.06
Nodes (49): Token X-Token (__TOKEN__), FastMCP("claudinho") transporte stdio, Júnior revisor visual, medir_cor, acao() /api/acao, animar(), api() fetch com X-Token, /api/estado endpoint (+41 more)

### Community 3 - "frases.py · esquetes.py"
Cohesion: 0.11
Nodes (14): escolher(), resultado_da_ideia(), sortear(), autoelogio(), categoria(), dados_do_dia(), escolher(), momento() (+6 more)

### Community 7 - "programas.py"
Cohesion: 0.05
Nodes (32): abrir_programa(), abrir_projeto(), atalho(), atalho_confirmado(), atalhos_conhecidos(), listar_programas(), ver_tela(), abrir() (+24 more)

### Community 8 - "subprocess"
Cohesion: 0.21
Nodes (6): icone(), main(), main(), passo(), _vram_livre_mb(), abrir_com_windows()

### Community 11 - "teclas.py"
Cohesion: 0.09
Nodes (17): _celulas(), _tabela(), _ler(), _palavras(), Mini cérebro (SQLite FTS5 lembranças), achar_janela(), apertar(), _apertar() (+9 more)

### Community 12 - "voz.py"
Cohesion: 0.14
Nodes (4): voz_pausada em tela cheia, microfones(), tocar(), _tom()

### Community 13 - "plano-mcp.md · plano-orquestrador.md"
Cohesion: 0.09
Nodes (17): Plano: contexto de projeto (sessões do Claude Code) pro Júnior, AJUDANTE / ABRIR_NA_MAO (regex sobre comandos Bash), Gancho ao_usar_ferramenta, ChatClaude (processo do chat, flags), Ferramentas com confirmação (fechar_programa, copiar, rodar_script, criar_arquivo), --permission-prompt-tool stdio → responder_controle → pedir_permissao, Plano: MCP exclusivo do Claudinho, Windows-MCP (genérico, não usar) (+9 more)

### Community 14 - "claudinho.pyw · comentários"
Cohesion: 0.11
Nodes (8): carregar_config(), gravar_json(), icone_mic(), ler_json(), _LimitesBasicos, mestre_do_perfil_antigo(), paginar(), trechos_marcantes()

### Community 17 - "consultas.js"
Cohesion: 0.20
Nodes (20): andar(), canal(), consultar(), esperarCarga(), extrairJSON(), historico(), inicio(), inscricoes() (+12 more)

### Community 19 - "skins.py"
Cohesion: 0.06
Nodes (14): quadrado(), misturar(), virada_ultron(), Emo no rock, Música (controles de mídia do Windows), Skins (cores, adereços, pacotes), winrt (Media.Control, Notifications), aplicar_pacote() (+6 more)

### Community 20 - ".transcrever_detalhado"
Cohesion: 0.20
Nodes (3): limpar_ruido(), preparar(), repetitivo()

### Community 21 - ".__init__"
Cohesion: 0.17
Nodes (4): cursor(), escala(), monitor(), MONITORINFO

### Community 22 - "sistema.py · instalar.py"
Cohesion: 0.24
Nodes (8): aviso_ligado(), comando_cli(), comando_texto(), _dpapi(), _e_nosso(), guardar_segredo(), _ler_settings(), ligar_aviso()

### Community 23 - "motores.py · chats"
Cohesion: 0.10
Nodes (6): ChatNenhum, ChatOllama, ChatSimples, configurar(), frases_completas(), _ollama_fluxo()

### Community 24 - "janelas.py"
Cohesion: 0.07
Nodes (30): abrir_programa(), abrir_site(), achar_atalho(), app_da_loja(), forcar_frente(), liberados(), main(), navegador_padrao() (+22 more)

### Community 25 - ".soltar_emoji"
Cohesion: 0.11
Nodes (4): fora_da_barra(), limitar(), fala(), final()

### Community 26 - ".estado_painel"
Cohesion: 0.16
Nodes (9): artista_de_rock(), tem_ia(), chave_api(), disponivel(), ollama_status(), _tem_modelo(), abre_com_windows(), claude_instalado() (+1 more)

### Community 27 - "claudinho.pyw · servidor"
Cohesion: 0.23
Nodes (9): extensao_conectada(), iniciar_servidor(), do_GET(), do_POST(), responder(), token_ok(), main(), ServidorUnico (+1 more)

### Community 28 - "manifest.json"
Cohesion: 0.17
Nodes (11): background, service_worker, content_scripts, description, host_permissions, icons, 128, manifest_version (+3 more)

### Community 29 - "fundo.js"
Cohesion: 0.33
Nodes (10): abasDe(), ciclo(), consultar(), escolher(), executar(), PERMITIDO, player, playerVivo() (+2 more)

### Community 30 - "normalizar"
Cohesion: 0.25
Nodes (4): achar_apelido(), frase_aberta(), normalizar(), registrar()

### Community 34 - ".resumir_tela"
Cohesion: 0.18
Nodes (5): comentar_musica(), comentar_tela(), em_jpeg(), sem_ia(), tom_das_piadas()

### Community 36 - "conversa.html"
Cohesion: 0.25
Nodes (6): /api/conversa endpoint, atualizar() polling /api/conversa, bolha(), Janela de conversa (conversa.html), markdown() conversor, print_anexado

### Community 37 - "plano-ver-tela.md"
Cohesion: 0.25
Nodes (7): PROMPT_SISTEMA, ImageGrab + em_jpeg (~1280 px, JPEG 80), FERRAMENTAS (motores.py) com tool_result de imagem, ver_tela(alvo) ferramenta MCP, Faixa nos olhos (vendado), Personalidade (Claudinho / Ultron), Piadas sobre a tela

### Community 41 - "claudinho_notificar.py"
Cohesion: 0.48
Nodes (3): main(), texto_de(), ultimos()

### Community 42 - "escrever_perfil"
Cohesion: 0.25
Nodes (3): escrever_perfil(), perfil_curto(), texto_do_mestre()

### Community 43 - "tela_cheia"
Cohesion: 0.22
Nodes (4): gpu_livre(), liberar_gpu_se_jogo(), _ollama(), tela_cheia()

### Community 46 - "motores.py"
Cohesion: 0.12
Nodes (15): baixar_modelo(), ChatAPI, _cliente(), completar(), _completar_api(), _completar_claude_code(), _completar_ollama(), env_limpo() (+7 more)

### Community 50 - "ytmusic.js"
Cohesion: 0.83
Nodes (3): botao(), controle(), fazer()

### Community 52 - "entrada"
Cohesion: 0.11
Nodes (6): caminho_do_navegador(), entrada(), rotulo_atual(), montar(), desenhar_icone(), montar_extensao()

### Community 55 - "README.md · painel"
Cohesion: 0.67
Nodes (3): Painel (painel.html), ~/.claudinho/config.json, Painel de configurações (app do Edge InPrivate, API com token)

## Knowledge Gaps
- **25 isolated node(s):** `Mini cérebro (SQLite FTS5 lembranças)`, `Ferramentas com confirmação (fechar_programa, copiar, rodar_script, criar_arquivo)`, `Windows-MCP (genérico, não usar)`, `voz_pausada em tela cheia`, `/api/estado endpoint` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 369 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Claudinho` connect `Claudinho` to `.resumir_tela`, `Balao`, `.acao_menu`, `.comentar_do_banco`, `escrever_perfil`, `tela_cheia`, `claudinho.pyw · comentários`, `.talvez_comentar_musica`, `skins.py`, `entrada`, `.__init__`, `motores.py · chats`, `janelas.py`, `.soltar_emoji`, `.estado_painel`, `claudinho.pyw · servidor`?**
  _High betweenness centrality (0.284) - this node is a cross-community bridge._
- **What connects `Mini cérebro (SQLite FTS5 lembranças)`, `Ferramentas com confirmação (fechar_programa, copiar, rodar_script, criar_arquivo)`, `Windows-MCP (genérico, não usar)` to the rest of the system?**
  _25 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `fala.py · stt.py` be split into smaller, more focused modules?**
  _Cohesion score 0.053939714436805924 - nodes in this community are weakly interconnected._
- **Why does `Memoria` connect `memoria.py · Memoria` to `teclas.py`, `.__init__`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Should `musica.py · notificacoes.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06428988895382817 - nodes in this community are weakly interconnected._
- **Why does `Voz` connect `Voz` to `._conversar`, `voz.py`, `.transcrever_detalhado`, `.__init__`, `normalizar`, `._ouvir_turno`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Should `carregar() polling /api/estado` be split into smaller, more focused modules?**
  _Cohesion score 0.05660377358490566 - nodes in this community are weakly interconnected._