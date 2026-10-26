# Graph Report - claudinho  (2026-10-26)

## Corpus Check
- 33 files · ~66,236 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 2, .spec 1)

## Summary
- 979 nodes · 1982 edges · 57 communities (36 shown, 21 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 67 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ced66fbb`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- fala.py · stt.py
- musica.py · notificacoes.py
- carregar() polling /api/estado
- frases.py · esquetes.py
- claudinho.pyw · Balao
- Claudinho
- memoria.py · Memoria
- .__init__
- requirements.txt (dependências Python)
- claudinho.pyw · esquetes
- claudinho.pyw · piadas
- Claudinho (mascote de mesa)
- abrir.py
- plano-mcp.md · plano-orquestrador.md
- claudinho.pyw · comentários
- claudinho.pyw · ChatClaude
- .acao_menu
- consultas.js
- Voz
- skins.py
- motores.py
- claudinho.pyw · bandeja e extensão
- sistema.py · instalar.py
- motores.py · chats
- janelas.py
- montarResto
- .estado_painel
- claudinho.pyw · servidor
- manifest.json
- fundo.js
- .perguntar
- .desenhar
- comentar_tela
- desenhar() sprite no canvas
- conversa.html
- plano-ver-tela.md
- Música (controles de mídia do Windows)
- Meu Mestre
- escrever_perfil
- motores.py · modo jogo
- claudinho_notificar.py
- claudinho.pyw · Gravador
- cli.py
- ytmusic.js
- motores.py · baixar_modelo
- claudinho.pyw · notificações
- claudinho.pyw · atalho
- README.md · painel
- trechos_marcantes
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
8. `listar()` - 12 edges
9. `ChatSimples` - 12 edges
10. `abrir_programa()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `trabalho()` --calls--> `tocar_no_youtube_music()`  [EXTRACTED]
  claudinho.pyw → musica.py
- `ver_tela(alvo) ferramenta MCP` --conceptually_related_to--> `Faixa nos olhos (vendado)`  [INFERRED]
  docs/plano-ver-tela.md → README.md
- `carregar_config()` --calls--> `configurar()`  [EXTRACTED]
  claudinho.pyw → motores.py
- `carregar_config()` --calls--> `visual_valido()`  [EXTRACTED]
  claudinho.pyw → skins.py
- `tem_ia()` --calls--> `disponivel()`  [EXTRACTED]
  claudinho.pyw → motores.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Páginas HTML que falam com a API local do Claudinho via X-Token** — conversa_atualizar, painel_api, conversa_x_token, conversa_api_conversa, painel_api_estado [INFERRED 0.85]
- **Ferramentas do servidor MCP do Claudinho** — claudinho_mcp, readme_mcp_do_claudinho, docs_plano_mcp_ferramentas_livres, docs_plano_mcp_ferramentas_com_confirmacao, docs_plano_ver_tela_ver_tela, docs_plano_orquestrador_rodar_tarefa [INFERRED 0.85]
- **Júnior vê, confere no código e despacha correção pro Claude Code** — painel_modo_junior, docs_plano_ver_tela_ver_tela, docs_plano_orquestrador_medir_cor, docs_plano_contexto_de_projeto_conferir_no_codigo, docs_plano_orquestrador_rodar_tarefa, docs_plano_orquestrador_projetos_liberados [INFERRED 0.85]

## Communities (57 total, 21 thin omitted)

### Community 0 - "fala.py · stt.py"
Cohesion: 0.06
Nodes (18): testar(), catalogo(), dividir_em_frases(), efeito_anime(), efeito_ultron(), eh_edge(), eh_kokoro(), Fala (+10 more)

### Community 1 - "musica.py · notificacoes.py"
Cohesion: 0.07
Nodes (29): abrir_aba_nova(), assistir(), buscar(), consultar(), consultar_ext(), controlar(), _controlar(), descrever() (+21 more)

### Community 2 - "carregar() polling /api/estado"
Cohesion: 0.21
Nodes (16): Token X-Token (__TOKEN__), acao() /api/acao, api() fetch com X-Token, /api/estado endpoint, atualizarVoz(), avisar() toast, carregar() polling /api/estado, montarMestre() (+8 more)

### Community 3 - "frases.py · esquetes.py"
Cohesion: 0.07
Nodes (17): escolher(), resultado_da_ideia(), sortear(), _celulas(), limpar(), _tabela(), autoelogio(), categoria() (+9 more)

### Community 4 - "claudinho.pyw · Balao"
Cohesion: 0.08
Nodes (5): Balao, em_jpeg(), icone_enviar(), icone_mic(), paginar()

### Community 7 - ".__init__"
Cohesion: 0.10
Nodes (3): cursor(), escala(), monitor()

### Community 8 - "requirements.txt (dependências Python)"
Cohesion: 0.18
Nodes (13): FastMCP("claudinho") transporte stdio, Reconhecimento da fala na nuvem (Groq) com volta pro Whisper, Tom da voz Microsoft (Thalita, Francisca, Antônio), Motor de IA (Claude Code / API / Ollama / nenhum), Voz (Whisper + Piper, palavra de chamada), anthropic>=0.80, customtkinter>=5.2, requirements.txt (dependências Python) (+5 more)

### Community 9 - "claudinho.pyw · esquetes"
Cohesion: 0.15
Nodes (5): fora_da_barra(), gravar_json(), limitar(), fala(), final()

### Community 11 - "Claudinho (mascote de mesa)"
Cohesion: 0.22
Nodes (8): Plano: contexto de projeto (sessões do Claude Code) pro Júnior, Júnior revisor visual, medir_cor, Plano: Claudinho orquestrador + Júnior revisor visual, Plano: olha o que está na tela e me responde, Modo Júnior (config modo_junior), Claudinho (mascote de mesa), pillow>=10.0

### Community 12 - "abrir.py"
Cohesion: 0.05
Nodes (33): abrir_programa(), abrir_site(), achar_atalho(), app_da_loja(), forcar_frente(), liberados(), main(), navegador_padrao() (+25 more)

### Community 13 - "plano-mcp.md · plano-orquestrador.md"
Cohesion: 0.13
Nodes (10): Gancho ao_usar_ferramenta, ChatClaude (processo do chat, flags), Ferramentas com confirmação (fechar_programa, copiar, rodar_script, criar_arquivo), --permission-prompt-tool stdio → responder_controle → pedir_permissao, Windows-MCP (genérico, não usar), projetos_liberados (config nome → pasta), rodar_tarefa(projeto, instrucao), Sessão headless claude -p stream-json (--resume) (+2 more)

### Community 14 - "claudinho.pyw · comentários"
Cohesion: 0.10
Nodes (10): artista_de_rock(), carregar_config(), _criar_job(), ler_json(), _LimitesBasicos, _LimitesEstendidos, mestre_do_perfil_antigo(), MONITORINFO (+2 more)

### Community 16 - ".acao_menu"
Cohesion: 0.11
Nodes (3): trabalho(), trabalho(), tem_ia()

### Community 17 - "consultas.js"
Cohesion: 0.20
Nodes (20): andar(), canal(), consultar(), esperarCarga(), extrairJSON(), historico(), inicio(), inscricoes() (+12 more)

### Community 18 - "Voz"
Cohesion: 0.05
Nodes (13): voz_pausada em tela cheia, achar_apelido(), frase_aberta(), limpar_ruido(), normalizar(), preparar(), registrar(), repetitivo() (+5 more)

### Community 19 - "skins.py"
Cohesion: 0.15
Nodes (7): aplicar_pacote(), autorretrato(), catalogo(), cor_do_corpo(), itens_vestidos(), pixels(), visual_valido()

### Community 20 - "motores.py"
Cohesion: 0.14
Nodes (14): ChatAPI, _cliente(), completar(), _completar_api(), _completar_claude_code(), _completar_ollama(), env_limpo(), _imagens_ollama() (+6 more)

### Community 21 - "claudinho.pyw · bandeja e extensão"
Cohesion: 0.11
Nodes (6): caminho_do_navegador(), entrada(), rotulo_atual(), montar(), desenhar_icone(), montar_extensao()

### Community 22 - "sistema.py · instalar.py"
Cohesion: 0.21
Nodes (9): main(), passo(), abrir_com_windows(), aviso_ligado(), comando_cli(), comando_texto(), _e_nosso(), _ler_settings() (+1 more)

### Community 23 - "motores.py · chats"
Cohesion: 0.13
Nodes (4): ChatNenhum, ChatOllama, ChatSimples, configurar()

### Community 24 - "janelas.py"
Cohesion: 0.09
Nodes (20): ver_tela(), Claudecímetro (projeto antigo), Gasto de tokens da sessão, Registro de sessões ~/.claude/sessions/<pid>.json, Módulo sessoes.py (listar, em_foco, uso), Transcript ~/.claude/projects/<pasta>/<sessionId>.jsonl (message.usage), Ferramentas livres (abrir_site, pesquisar, abrir_programa, musica, volume, focar_janela, lembrete, modo_foco), Servidor HTTP local porta 47821 (/aviso, /lembrete, /foco) (+12 more)

### Community 25 - "montarResto"
Cohesion: 0.25
Nodes (9): atualizarVivos(), Modal de instalação da extensão, montarPastas(), montarResto(), Pastas que o chat lê sem perguntar, Consultar YouTube/YT Music via extensão (musica.py consultar/ir), Extensão do navegador (ext_token, polling 127.0.0.1), YouTube Music (ytmusicapi, rádio) (+1 more)

### Community 26 - ".estado_painel"
Cohesion: 0.14
Nodes (12): extensao_conectada(), sem_ia(), chave_api(), disponivel(), ollama_status(), _tem_modelo(), abre_com_windows(), claude_instalado() (+4 more)

### Community 27 - "claudinho.pyw · servidor"
Cohesion: 0.25
Nodes (8): iniciar_servidor(), do_GET(), do_POST(), responder(), token_ok(), main(), ServidorUnico, versao_da_extensao()

### Community 28 - "manifest.json"
Cohesion: 0.17
Nodes (11): background, service_worker, content_scripts, description, host_permissions, icons, 128, manifest_version (+3 more)

### Community 29 - "fundo.js"
Cohesion: 0.33
Nodes (10): abasDe(), ciclo(), consultar(), escolher(), executar(), PERMITIDO, player, playerVivo() (+2 more)

### Community 34 - "comentar_tela"
Cohesion: 0.29
Nodes (4): trabalho(), comentar_musica(), comentar_tela(), tom_das_piadas()

### Community 35 - "desenhar() sprite no canvas"
Cohesion: 0.50
Nodes (5): animar(), corDoCorpo(), desenhar() sprite no canvas, hsv() arco-íris, pixelsDoAdereco()

### Community 36 - "conversa.html"
Cohesion: 0.25
Nodes (6): /api/conversa endpoint, atualizar() polling /api/conversa, bolha(), Janela de conversa (conversa.html), markdown() conversor, print_anexado

### Community 37 - "plano-ver-tela.md"
Cohesion: 0.25
Nodes (7): PROMPT_SISTEMA, ImageGrab + em_jpeg (~1280 px, JPEG 80), FERRAMENTAS (motores.py) com tool_result de imagem, ver_tela(alvo) ferramenta MCP, Faixa nos olhos (vendado), Personalidade (Claudinho / Ultron), Piadas sobre a tela

### Community 38 - "Música (controles de mídia do Windows)"
Cohesion: 0.50
Nodes (4): Emo no rock, Música (controles de mídia do Windows), Skins (cores, adereços, pacotes), winrt (Media.Control, Notifications)

### Community 42 - "escrever_perfil"
Cohesion: 0.25
Nodes (3): escrever_perfil(), perfil_curto(), texto_do_mestre()

### Community 43 - "motores.py · modo jogo"
Cohesion: 0.22
Nodes (4): gpu_livre(), liberar_gpu_se_jogo(), _ollama(), tela_cheia()

### Community 46 - "claudinho_notificar.py"
Cohesion: 0.48
Nodes (3): main(), texto_de(), ultimos()

### Community 50 - "ytmusic.js"
Cohesion: 0.83
Nodes (3): botao(), controle(), fazer()

### Community 55 - "README.md · painel"
Cohesion: 0.67
Nodes (3): Painel (painel.html), ~/.claudinho/config.json, Painel de configurações (app do Edge InPrivate, API com token)

## Knowledge Gaps
- **25 isolated node(s):** `Ferramentas com confirmação (fechar_programa, copiar, rodar_script, criar_arquivo)`, `Windows-MCP (genérico, não usar)`, `/api/estado endpoint`, `Modal de instalação da extensão`, `Pastas que o chat lê sem perguntar` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 345 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Claudinho` connect `Claudinho` to `.desenhar`, `.tick`, `frases.py · esquetes.py`, `claudinho.pyw · Balao`, `.__init__`, `claudinho.pyw · esquetes`, `claudinho.pyw · piadas`, `escrever_perfil`, `motores.py · modo jogo`, `claudinho.pyw · comentários`, `.acao_menu`, `claudinho.pyw · bandeja e extensão`, `motores.py · chats`, `janelas.py`, `.estado_painel`, `claudinho.pyw · servidor`, `.animar_voz`?**
  _High betweenness centrality (0.278) - this node is a cross-community bridge._
- **What connects `Ferramentas com confirmação (fechar_programa, copiar, rodar_script, criar_arquivo)`, `Windows-MCP (genérico, não usar)`, `/api/estado endpoint` to the rest of the system?**
  _25 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `fala.py · stt.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05593220338983051 - nodes in this community are weakly interconnected._
- **Why does `Voz` connect `Voz` to `.__init__`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Should `musica.py · notificacoes.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06948051948051948 - nodes in this community are weakly interconnected._
- **Why does `Memoria` connect `memoria.py · Memoria` to `abrir.py`, `.__init__`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Should `frases.py · esquetes.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06755260243632337 - nodes in this community are weakly interconnected._