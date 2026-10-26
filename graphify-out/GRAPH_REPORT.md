# Graph Report - claudinho  (2026-10-26)

## Corpus Check
- 39 files · ~78,234 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 2, .spec 1)

## Summary
- 1112 nodes · 2266 edges · 63 communities (34 shown, 29 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 74 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1c5f1a88`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Fala
- musica.py · notificacoes.py
- carregar() polling /api/estado
- frases.py · esquetes.py
- Balao
- .processar_eventos
- memoria.py · Memoria
- programas.py
- .estado_painel
- .talvez_comentar
- .comentar_do_banco
- claudinho_mcp.py
- formatar.py
- rodar_tarefa(projeto, instrucao)
- claudinho.pyw · comentários
- claudinho.pyw · ChatClaude
- Claudinho
- consultas.js
- Voz
- skins.py
- rotinas.js
- .__init__
- sistema.py
- ChatSimples
- time
- .comentar
- tela_cheia
- claudinho.pyw · servidor
- manifest.json
- fundo.js
- .desenhar
- comentar_tela
- .perguntar
- _criar_job
- motores.py
- conversa.html
- plano-ver-tela.md
- subprocess
- voz.py
- .transcrever_detalhado
- artista_de_rock
- escrever_perfil
- chave_da_extensao
- normalizar
- ._ouvir_turno
- claudinho.pyw · Gravador
- montar
- gravador.js
- ytmusic.js
- cli.py
- entrada
- iniciar_atalho
- README.md · painel
- .acao_menu
- virada_ultron
- plano-ver-tela.md · atalhos
- plano-ver-tela.md · resumir
- painel.html · modo jogo
- README.md · autoconfiança
- README.md · chat rápido

## God Nodes (most connected - your core abstractions)
1. `Claudinho` - 135 edges
2. `Memoria` - 30 edges
3. `Voz` - 30 edges
4. `Balao` - 25 edges
5. `Fala` - 17 edges
6. `ChatClaude` - 16 edges
7. `main()` - 16 edges
8. `listar()` - 14 edges
9. `ChatSimples` - 13 edges
10. `monitor()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `trabalho()` --indirect_call--> `lista()`  [INFERRED]
  claudinho.pyw → rotinas.py
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

## Communities (63 total, 29 thin omitted)

### Community 0 - "Fala"
Cohesion: 0.06
Nodes (17): catalogo(), dividir_em_frases(), efeito_anime(), efeito_ultron(), eh_edge(), eh_kokoro(), Fala, trabalhar() (+9 more)

### Community 1 - "musica.py · notificacoes.py"
Cohesion: 0.06
Nodes (31): trabalho(), trabalho(), resumir_notificacoes(), abrir_aba_nova(), assistir(), buscar(), consultar(), consultar_ext() (+23 more)

### Community 2 - "carregar() polling /api/estado"
Cohesion: 0.06
Nodes (49): Token X-Token (__TOKEN__), FastMCP("claudinho") transporte stdio, Júnior revisor visual, medir_cor, acao() /api/acao, animar(), api() fetch com X-Token, /api/estado endpoint (+41 more)

### Community 3 - "frases.py · esquetes.py"
Cohesion: 0.09
Nodes (16): escolher(), fala(), final(), resultado_da_ideia(), sortear(), autoelogio(), categoria(), dados_do_dia() (+8 more)

### Community 4 - "Balao"
Cohesion: 0.08
Nodes (5): Balao, em_jpeg(), icone_enviar(), icone_mic(), paginar()

### Community 7 - "programas.py"
Cohesion: 0.07
Nodes (29): main(), texto_de(), ultimos(), _ler(), abrir(), achar(), _alvos_dos_atalhos(), _apps_iniciar() (+21 more)

### Community 8 - ".estado_painel"
Cohesion: 0.19
Nodes (7): extensao_conectada(), configurar(), disponivel(), ollama_status(), _tem_modelo(), abre_com_windows(), claude_instalado()

### Community 11 - "claudinho_mcp.py"
Cohesion: 0.05
Nodes (38): trabalho(), abrir_programa(), abrir_projeto(), atalho(), atalho_confirmado(), atalhos_conhecidos(), esperar_janela(), listar_programas() (+30 more)

### Community 13 - "rodar_tarefa(projeto, instrucao)"
Cohesion: 0.09
Nodes (17): Plano: contexto de projeto (sessões do Claude Code) pro Júnior, AJUDANTE / ABRIR_NA_MAO (regex sobre comandos Bash), Gancho ao_usar_ferramenta, ChatClaude (processo do chat, flags), Ferramentas com confirmação (fechar_programa, copiar, rodar_script, criar_arquivo), --permission-prompt-tool stdio → responder_controle → pedir_permissao, Plano: MCP exclusivo do Claudinho, Windows-MCP (genérico, não usar) (+9 more)

### Community 14 - "claudinho.pyw · comentários"
Cohesion: 0.10
Nodes (10): caminho_do_navegador(), carregar_config(), escala(), gravar_json(), ler_json(), _LimitesBasicos, mestre_do_perfil_antigo(), MONITORINFO (+2 more)

### Community 17 - "consultas.js"
Cohesion: 0.20
Nodes (20): andar(), canal(), consultar(), esperarCarga(), extrairJSON(), historico(), inicio(), inscricoes() (+12 more)

### Community 19 - "skins.py"
Cohesion: 0.10
Nodes (12): Emo no rock, Música (controles de mídia do Windows), Skins (cores, adereços, pacotes), winrt (Media.Control, Notifications), aplicar_pacote(), autorretrato(), catalogo(), cor_do_corpo() (+4 more)

### Community 20 - "rotinas.js"
Cohesion: 0.26
Nodes (11): anotar(), carregada(), comecar(), descrever(), fazerPasso(), gravacao(), guardar(), mensagem() (+3 more)

### Community 22 - "sistema.py"
Cohesion: 0.19
Nodes (11): testar(), aviso_ligado(), comando_cli(), comando_texto(), _dpapi(), _e_nosso(), guardar_segredo(), lancar() (+3 more)

### Community 23 - "ChatSimples"
Cohesion: 0.14
Nodes (3): ChatAPI, ChatNenhum, ChatSimples

### Community 24 - "time"
Cohesion: 0.07
Nodes (34): abrir_programa(), abrir_site(), achar_atalho(), app_da_loja(), forcar_frente(), liberados(), main(), navegador_padrao() (+26 more)

### Community 27 - "claudinho.pyw · servidor"
Cohesion: 0.25
Nodes (8): iniciar_servidor(), do_GET(), do_POST(), responder(), token_ok(), main(), ServidorUnico, versao_da_extensao()

### Community 28 - "manifest.json"
Cohesion: 0.11
Nodes (17): action, default_icon, default_popup, default_title, background, service_worker, content_scripts, 128 (+9 more)

### Community 29 - "fundo.js"
Cohesion: 0.33
Nodes (10): abasDe(), ciclo(), consultar(), escolher(), executar(), PERMITIDO, player, playerVivo() (+2 more)

### Community 31 - "comentar_tela"
Cohesion: 0.33
Nodes (3): comentar_musica(), comentar_tela(), tom_das_piadas()

### Community 32 - ".perguntar"
Cohesion: 0.22
Nodes (6): chave_api(), _cliente(), _completar_api(), _pedido_api(), rodar_ajudante(), _texto_da_resposta()

### Community 35 - "motores.py"
Cohesion: 0.11
Nodes (13): baixar_modelo(), ChatOllama, completar(), _completar_claude_code(), _completar_ollama(), env_limpo(), frases_completas(), _imagens_ollama() (+5 more)

### Community 36 - "conversa.html"
Cohesion: 0.25
Nodes (6): /api/conversa endpoint, atualizar() polling /api/conversa, bolha(), Janela de conversa (conversa.html), markdown() conversor, print_anexado

### Community 37 - "plano-ver-tela.md"
Cohesion: 0.25
Nodes (7): PROMPT_SISTEMA, ImageGrab + em_jpeg (~1280 px, JPEG 80), FERRAMENTAS (motores.py) com tool_result de imagem, ver_tela(alvo) ferramenta MCP, Faixa nos olhos (vendado), Personalidade (Claudinho / Ultron), Piadas sobre a tela

### Community 38 - "subprocess"
Cohesion: 0.21
Nodes (7): icone(), main(), main(), passo(), rodar_claude(), _vram_livre_mb(), abrir_com_windows()

### Community 39 - "voz.py"
Cohesion: 0.14
Nodes (4): voz_pausada em tela cheia, microfones(), tocar(), _tom()

### Community 40 - ".transcrever_detalhado"
Cohesion: 0.20
Nodes (3): limpar_ruido(), preparar(), repetitivo()

### Community 42 - "escrever_perfil"
Cohesion: 0.25
Nodes (3): escrever_perfil(), perfil_curto(), texto_do_mestre()

### Community 44 - "normalizar"
Cohesion: 0.25
Nodes (4): achar_apelido(), frase_aberta(), normalizar(), registrar()

### Community 48 - "montar"
Cohesion: 0.53
Nodes (5): caixa, descrever(), html(), montar(), pedir()

### Community 49 - "gravador.js"
Cohesion: 0.47
Nodes (3): alvo(), rotuloDe(), seletor()

### Community 50 - "ytmusic.js"
Cohesion: 0.83
Nodes (3): botao(), controle(), fazer()

### Community 52 - "entrada"
Cohesion: 0.13
Nodes (5): entrada(), rotulo_atual(), montar(), desenhar_icone(), montar_extensao()

### Community 55 - "README.md · painel"
Cohesion: 0.67
Nodes (3): Painel (painel.html), ~/.claudinho/config.json, Painel de configurações (app do Edge InPrivate, API com token)

## Knowledge Gaps
- **25 isolated node(s):** `Ferramentas com confirmação (fechar_programa, copiar, rodar_script, criar_arquivo)`, `Windows-MCP (genérico, não usar)`, `/api/estado endpoint`, `Modal de instalação da extensão`, `Pastas que o chat lê sem perguntar` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 396 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Claudinho` connect `Claudinho` to `.tick`, `Balao`, `.processar_eventos`, `.estado_painel`, `.talvez_comentar`, `.comentar_do_banco`, `claudinho_mcp.py`, `escrever_perfil`, `claudinho.pyw · comentários`, `entrada`, `.__init__`, `.desenhar`, `ChatSimples`, `.acao_menu`, `tela_cheia`, `claudinho.pyw · servidor`, `.comentar`?**
  _High betweenness centrality (0.272) - this node is a cross-community bridge._
- **What connects `Ferramentas com confirmação (fechar_programa, copiar, rodar_script, criar_arquivo)`, `Windows-MCP (genérico, não usar)`, `/api/estado endpoint` to the rest of the system?**
  _25 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Fala` be split into smaller, more focused modules?**
  _Cohesion score 0.05727644652250146 - nodes in this community are weakly interconnected._
- **Why does `Voz` connect `Voz` to `voz.py`, `.transcrever_detalhado`, `normalizar`, `._ouvir_turno`, `.__init__`, `._conversar`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Should `musica.py · notificacoes.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06428988895382817 - nodes in this community are weakly interconnected._
- **Why does `Memoria` connect `memoria.py · Memoria` to `.__init__`, `programas.py`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Should `carregar() polling /api/estado` be split into smaller, more focused modules?**
  _Cohesion score 0.05660377358490566 - nodes in this community are weakly interconnected._