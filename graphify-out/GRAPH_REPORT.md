# Graph Report - claudinho  (2026-10-26)

## Corpus Check
- 34 files · ~68,802 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 2, .spec 1)

## Summary
- 1008 nodes · 2047 edges · 62 communities (36 shown, 26 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 67 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c3918135`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- fala.py · stt.py
- musica.py · notificacoes.py
- carregar() polling /api/estado
- frases.py · esquetes.py
- claudinho.pyw · Balao
- memoria.py · Memoria
- .__init__
- claudinho_mcp.py
- claudinho.pyw · esquetes
- .comentar_do_banco
- teclas.py
- abrir.py
- plano-mcp.md · plano-orquestrador.md
- claudinho.pyw · comentários
- claudinho.pyw · ChatClaude
- .talvez_comentar
- consultas.js
- Voz
- skins.py
- motores.py
- claudinho.pyw · bandeja e extensão
- sistema.py · instalar.py
- motores.py · chats
- janelas.py
- ._ouvir_turno
- .estado_painel
- claudinho.pyw · servidor
- manifest.json
- fundo.js
- ._ouvir_turno
- Claudinho
- comentar_tela
- voz.py
- conversa.html
- plano-ver-tela.md
- .mostrar
- Módulo sessoes.py (listar, em_foco, uso)
- claudinho_notificar.py
- escrever_perfil
- formatar.py
- preparar
- motores.py
- claudinho.pyw · Gravador
- Ferramentas livres (abrir_site, pesquisar, abrir_programa, musica, volume, focar_janela, lembrete, modo_foco)
- threading
- ytmusic.js
- _criar_job
- caminho_do_navegador
- claudinho.pyw · atalho
- README.md · painel
- normalizar
- plano-ver-tela.md · atalhos
- plano-ver-tela.md · resumir
- painel.html · modo jogo
- README.md · autoconfiança
- README.md · chat rápido

## God Nodes (most connected - your core abstractions)
1. `Claudinho` - 133 edges
2. `Memoria` - 30 edges
3. `Voz` - 30 edges
4. `Balao` - 25 edges
5. `Fala` - 17 edges
6. `main()` - 16 edges
7. `ChatClaude` - 14 edges
8. `listar()` - 14 edges
9. `ChatSimples` - 12 edges
10. `abrir_programa()` - 11 edges

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

## Communities (62 total, 26 thin omitted)

### Community 0 - "fala.py · stt.py"
Cohesion: 0.06
Nodes (18): testar(), catalogo(), dividir_em_frases(), efeito_anime(), efeito_ultron(), eh_edge(), eh_kokoro(), Fala (+10 more)

### Community 1 - "musica.py · notificacoes.py"
Cohesion: 0.06
Nodes (31): trabalho(), resumir_notificacoes(), abrir_aba_nova(), assistir(), buscar(), consultar(), consultar_ext(), controlar() (+23 more)

### Community 2 - "carregar() polling /api/estado"
Cohesion: 0.06
Nodes (48): FastMCP("claudinho") transporte stdio, Júnior revisor visual, medir_cor, acao() /api/acao, animar(), api() fetch com X-Token, /api/estado endpoint, atualizarVivos() (+40 more)

### Community 3 - "frases.py · esquetes.py"
Cohesion: 0.10
Nodes (14): escolher(), resultado_da_ideia(), sortear(), autoelogio(), categoria(), dados_do_dia(), escolher(), momento() (+6 more)

### Community 4 - "claudinho.pyw · Balao"
Cohesion: 0.08
Nodes (5): Balao, em_jpeg(), icone_enviar(), icone_mic(), paginar()

### Community 8 - "claudinho_mcp.py"
Cohesion: 0.16
Nodes (6): abrir_programa(), atalho(), atalho_confirmado(), atalhos_conhecidos(), ver_tela(), bloqueio()

### Community 9 - "claudinho.pyw · esquetes"
Cohesion: 0.13
Nodes (4): fora_da_barra(), limitar(), fala(), final()

### Community 11 - "teclas.py"
Cohesion: 0.16
Nodes (12): achar_janela(), apertar(), _apertar(), catalogo(), _config(), entender(), faixa(), _limpo() (+4 more)

### Community 12 - "abrir.py"
Cohesion: 0.06
Nodes (31): abrir_programa(), abrir_site(), achar_atalho(), app_da_loja(), forcar_frente(), liberados(), main(), navegador_padrao() (+23 more)

### Community 13 - "plano-mcp.md · plano-orquestrador.md"
Cohesion: 0.09
Nodes (17): Plano: contexto de projeto (sessões do Claude Code) pro Júnior, AJUDANTE / ABRIR_NA_MAO (regex sobre comandos Bash), Gancho ao_usar_ferramenta, ChatClaude (processo do chat, flags), Ferramentas com confirmação (fechar_programa, copiar, rodar_script, criar_arquivo), --permission-prompt-tool stdio → responder_controle → pedir_permissao, Plano: MCP exclusivo do Claudinho, Windows-MCP (genérico, não usar) (+9 more)

### Community 14 - "claudinho.pyw · comentários"
Cohesion: 0.10
Nodes (10): artista_de_rock(), carregar_config(), chave_da_extensao(), escala(), gravar_json(), ler_json(), _LimitesBasicos, mestre_do_perfil_antigo() (+2 more)

### Community 16 - ".talvez_comentar"
Cohesion: 0.12
Nodes (4): trabalho(), trabalho(), sem_ia(), tem_ia()

### Community 17 - "consultas.js"
Cohesion: 0.20
Nodes (20): andar(), canal(), consultar(), esperarCarga(), extrairJSON(), historico(), inicio(), inscricoes() (+12 more)

### Community 19 - "skins.py"
Cohesion: 0.07
Nodes (14): quadrado(), misturar(), virada_ultron(), Emo no rock, Música (controles de mídia do Windows), Skins (cores, adereços, pacotes), winrt (Media.Control, Notifications), aplicar_pacote() (+6 more)

### Community 20 - "motores.py"
Cohesion: 0.18
Nodes (5): _completar_api(), _pedido_api(), rodar_ajudante(), _texto_da_resposta(), ver_tela()

### Community 21 - "claudinho.pyw · bandeja e extensão"
Cohesion: 0.13
Nodes (5): entrada(), rotulo_atual(), montar(), desenhar_icone(), montar_extensao()

### Community 22 - "sistema.py · instalar.py"
Cohesion: 0.18
Nodes (10): Release com PyInstaller (Claudinho.exe + claudinho-cli.exe), aviso_ligado(), comando_cli(), comando_texto(), _dpapi(), _e_nosso(), guardar_segredo(), ler_segredo() (+2 more)

### Community 23 - "motores.py · chats"
Cohesion: 0.11
Nodes (6): ChatAPI, ChatNenhum, ChatOllama, ChatSimples, configurar(), frases_completas()

### Community 24 - "janelas.py"
Cohesion: 0.17
Nodes (11): descrever(), exe_de(), janela_ativa(), listar(), cb(), oculta(), capturar(), janela_da_frente() (+3 more)

### Community 25 - "._ouvir_turno"
Cohesion: 0.25
Nodes (4): achar_apelido(), frase_aberta(), normalizar(), registrar()

### Community 26 - ".estado_painel"
Cohesion: 0.25
Nodes (7): chave_api(), _cliente(), disponivel(), ollama_status(), _tem_modelo(), abre_com_windows(), claude_instalado()

### Community 27 - "claudinho.pyw · servidor"
Cohesion: 0.23
Nodes (9): extensao_conectada(), iniciar_servidor(), do_GET(), do_POST(), responder(), token_ok(), main(), ServidorUnico (+1 more)

### Community 28 - "manifest.json"
Cohesion: 0.17
Nodes (11): background, service_worker, content_scripts, description, host_permissions, icons, 128, manifest_version (+3 more)

### Community 29 - "fundo.js"
Cohesion: 0.33
Nodes (10): abasDe(), ciclo(), consultar(), escolher(), executar(), PERMITIDO, player, playerVivo() (+2 more)

### Community 34 - "comentar_tela"
Cohesion: 0.33
Nodes (3): comentar_musica(), comentar_tela(), tom_das_piadas()

### Community 35 - "voz.py"
Cohesion: 0.14
Nodes (4): voz_pausada em tela cheia, microfones(), tocar(), _tom()

### Community 36 - "conversa.html"
Cohesion: 0.22
Nodes (7): /api/conversa endpoint, atualizar() polling /api/conversa, bolha(), Janela de conversa (conversa.html), markdown() conversor, Token X-Token (__TOKEN__), print_anexado

### Community 37 - "plano-ver-tela.md"
Cohesion: 0.25
Nodes (7): PROMPT_SISTEMA, ImageGrab + em_jpeg (~1280 px, JPEG 80), FERRAMENTAS (motores.py) com tool_result de imagem, ver_tela(alvo) ferramenta MCP, Faixa nos olhos (vendado), Personalidade (Claudinho / Ultron), Piadas sobre a tela

### Community 39 - "Módulo sessoes.py (listar, em_foco, uso)"
Cohesion: 0.33
Nodes (5): Claudecímetro (projeto antigo), Gasto de tokens da sessão, Registro de sessões ~/.claude/sessions/<pid>.json, Módulo sessoes.py (listar, em_foco, uso), Transcript ~/.claude/projects/<pasta>/<sessionId>.jsonl (message.usage)

### Community 41 - "claudinho_notificar.py"
Cohesion: 0.47
Nodes (3): main(), texto_de(), ultimos()

### Community 42 - "escrever_perfil"
Cohesion: 0.25
Nodes (3): escrever_perfil(), perfil_curto(), texto_do_mestre()

### Community 45 - "preparar"
Cohesion: 0.20
Nodes (3): limpar_ruido(), preparar(), repetitivo()

### Community 46 - "motores.py"
Cohesion: 0.15
Nodes (13): completar(), _completar_claude_code(), _completar_ollama(), env_limpo(), gpu_livre(), _imagens_ollama(), liberar_gpu_se_jogo(), _ollama() (+5 more)

### Community 48 - "Ferramentas livres (abrir_site, pesquisar, abrir_programa, musica, volume, focar_janela, lembrete, modo_foco)"
Cohesion: 0.33
Nodes (3): Ferramentas livres (abrir_site, pesquisar, abrir_programa, musica, volume, focar_janela, lembrete, modo_foco), Servidor HTTP local porta 47821 (/aviso, /lembrete, /foco), no_ponto()

### Community 50 - "ytmusic.js"
Cohesion: 0.83
Nodes (3): botao(), controle(), fazer()

### Community 55 - "README.md · painel"
Cohesion: 0.67
Nodes (3): Painel (painel.html), ~/.claudinho/config.json, Painel de configurações (app do Edge InPrivate, API com token)

## Knowledge Gaps
- **25 isolated node(s):** `Ferramentas com confirmação (fechar_programa, copiar, rodar_script, criar_arquivo)`, `Windows-MCP (genérico, não usar)`, `/api/estado endpoint`, `Modal de instalação da extensão`, `Pastas que o chat lê sem perguntar` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 358 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Claudinho` connect `Claudinho` to `.tick`, `claudinho.pyw · Balao`, `.processar_eventos`, `.mostrar`, `.__init__`, `.acao_menu`, `claudinho.pyw · esquetes`, `.comentar_do_banco`, `escrever_perfil`, `.voz_pausada`, `claudinho.pyw · comentários`, `.talvez_comentar`, `skins.py`, `claudinho.pyw · bandeja e extensão`, `motores.py · chats`, `janelas.py`, `.estado_painel`, `claudinho.pyw · servidor`?**
  _High betweenness centrality (0.290) - this node is a cross-community bridge._
- **What connects `Ferramentas com confirmação (fechar_programa, copiar, rodar_script, criar_arquivo)`, `Windows-MCP (genérico, não usar)`, `/api/estado endpoint` to the rest of the system?**
  _25 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `fala.py · stt.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05593220338983051 - nodes in this community are weakly interconnected._
- **Why does `Balao` connect `claudinho.pyw · Balao` to `.mostrar`, `.processar_eventos`, `claudinho.pyw · comentários`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Should `musica.py · notificacoes.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06428988895382817 - nodes in this community are weakly interconnected._
- **Why does `Memoria` connect `memoria.py · Memoria` to `abrir.py`, `.__init__`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Should `carregar() polling /api/estado` be split into smaller, more focused modules?**
  _Cohesion score 0.058069381598793365 - nodes in this community are weakly interconnected._