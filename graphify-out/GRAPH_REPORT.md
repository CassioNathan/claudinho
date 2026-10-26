# Graph Report - claudinho  (2026-10-26)

## Corpus Check
- 35 files · ~71,508 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 2, .spec 1)

## Summary
- 1043 nodes · 2135 edges · 69 communities (46 shown, 23 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 67 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f1a02652`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Fala
- musica.py · notificacoes.py
- carregar() polling /api/estado
- frases.py · esquetes.py
- Balao
- memoria.py · Memoria
- programas.py
- time
- .acao_menu
- .comentar_do_banco
- teclas.py
- voz.py
- rodar_tarefa(projeto, instrucao)
- claudinho.pyw · comentários
- claudinho.pyw · ChatClaude
- Claudinho
- consultas.js
- Voz
- skins.py
- stt.py
- .__init__
- claudinho_mcp.py
- motores.py · chats
- sistema.py
- .area
- disponivel
- claudinho.pyw · servidor
- manifest.json
- fundo.js
- .desenhar
- requirements.txt (dependências Python)
- projetos.py
- limpar
- completar
- .perguntar
- conversa.html
- plano-ver-tela.md
- .__init__
- .parecida
- json
- escrever_perfil
- tela_cheia
- .instalar_extensao
- .tick
- motores.py
- claudinho.pyw · Gravador
- Claudinho (mascote de mesa)
- ytmusic.js
- Júnior revisor visual
- entrada
- --permission-prompt-tool stdio → responder_controle → pedir_permissao
- README.md · painel
- Módulo sessoes.py (listar, em_foco, uso)
- desenhar() sprite no canvas
- plano-ver-tela.md · atalhos
- plano-ver-tela.md · resumir
- painel.html · modo jogo
- README.md · autoconfiança
- README.md · chat rápido
- Extensão do navegador (ext_token, polling 127.0.0.1)
- baixar_modelo
- montarVisual
- Meu Mestre

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

## Communities (69 total, 23 thin omitted)

### Community 0 - "Fala"
Cohesion: 0.11
Nodes (7): catalogo(), eh_edge(), eh_kokoro(), Fala, trabalhar(), trabalhar(), instalada()

### Community 1 - "musica.py · notificacoes.py"
Cohesion: 0.06
Nodes (33): trabalho(), resumir_notificacoes(), Ferramentas livres (abrir_site, pesquisar, abrir_programa, musica, volume, focar_janela, lembrete, modo_foco), Servidor HTTP local porta 47821 (/aviso, /lembrete, /foco), abrir_aba_nova(), assistir(), buscar(), consultar() (+25 more)

### Community 2 - "carregar() polling /api/estado"
Cohesion: 0.23
Nodes (18): acao() /api/acao, api() fetch com X-Token, /api/estado endpoint, atualizarVivos(), atualizarVoz(), avisar() toast, carregar() polling /api/estado, montarMestre() (+10 more)

### Community 3 - "frases.py · esquetes.py"
Cohesion: 0.09
Nodes (16): escolher(), fala(), final(), resultado_da_ideia(), sortear(), autoelogio(), categoria(), dados_do_dia() (+8 more)

### Community 7 - "programas.py"
Cohesion: 0.11
Nodes (17): abrir(), achar(), _alvos_dos_atalhos(), _apps_iniciar(), bloqueados(), esta_bloqueado(), exe_bloqueado(), _exes() (+9 more)

### Community 8 - "time"
Cohesion: 0.16
Nodes (13): ver_tela(), _cpu_segundos(), descrever(), esperar_pronta(), exe_de(), cb(), oculta(), bloqueio() (+5 more)

### Community 9 - ".acao_menu"
Cohesion: 0.09
Nodes (4): trabalho(), trabalho(), sem_ia(), tem_ia()

### Community 10 - ".comentar_do_banco"
Cohesion: 0.08
Nodes (3): trabalho(), listar(), no_ponto()

### Community 11 - "teclas.py"
Cohesion: 0.14
Nodes (13): achar_janela(), apertar(), _apertar(), catalogo(), _config(), entender(), esperar(), faixa() (+5 more)

### Community 12 - "voz.py"
Cohesion: 0.13
Nodes (5): voz_pausada em tela cheia, dividir_em_frases(), limpar_para_fala(), so_o_comeco(), _tom()

### Community 13 - "rodar_tarefa(projeto, instrucao)"
Cohesion: 0.25
Nodes (6): Gancho ao_usar_ferramenta, projetos_liberados (config nome → pasta), rodar_tarefa(projeto, instrucao), Sessão headless claude -p stream-json (--resume), Avisos em fila (chat do Claude Code terminou), Hook Stop claudinho_notificar

### Community 14 - "claudinho.pyw · comentários"
Cohesion: 0.11
Nodes (9): carregar_config(), chave_da_extensao(), _criar_job(), gravar_json(), ler_json(), _LimitesBasicos, _LimitesEstendidos, mestre_do_perfil_antigo() (+1 more)

### Community 17 - "consultas.js"
Cohesion: 0.20
Nodes (20): andar(), canal(), consultar(), esperarCarga(), extrairJSON(), historico(), inicio(), inscricoes() (+12 more)

### Community 18 - "Voz"
Cohesion: 0.06
Nodes (11): achar_apelido(), frase_aberta(), limpar_ruido(), normalizar(), preparar(), registrar(), repetitivo(), tocar() (+3 more)

### Community 19 - "skins.py"
Cohesion: 0.11
Nodes (11): Emo no rock, Música (controles de mídia do Windows), Skins (cores, adereços, pacotes), winrt (Media.Control, Notifications), aplicar_pacote(), autorretrato(), catalogo(), cor_do_corpo() (+3 more)

### Community 20 - "stt.py"
Cohesion: 0.15
Nodes (7): efeito_anime(), efeito_ultron(), ErroSTT, _multipart(), testar(), transcrever(), _wav()

### Community 21 - ".__init__"
Cohesion: 0.16
Nodes (5): cursor(), escala(), iniciar_atalho(), monitor(), MONITORINFO

### Community 22 - "claudinho_mcp.py"
Cohesion: 0.15
Nodes (7): abrir_programa(), abrir_projeto(), atalho(), atalho_confirmado(), atalhos_conhecidos(), esperar_janela(), listar_programas()

### Community 23 - "motores.py · chats"
Cohesion: 0.17
Nodes (3): ChatNenhum, ChatOllama, ChatSimples

### Community 24 - "sistema.py"
Cohesion: 0.06
Nodes (31): abrir_programa(), abrir_site(), achar_atalho(), app_da_loja(), forcar_frente(), liberados(), main(), navegador_padrao() (+23 more)

### Community 26 - "disponivel"
Cohesion: 0.29
Nodes (4): configurar(), disponivel(), ollama_status(), _tem_modelo()

### Community 27 - "claudinho.pyw · servidor"
Cohesion: 0.25
Nodes (8): iniciar_servidor(), do_GET(), do_POST(), responder(), token_ok(), main(), ServidorUnico, versao_da_extensao()

### Community 28 - "manifest.json"
Cohesion: 0.17
Nodes (11): background, service_worker, content_scripts, description, host_permissions, icons, 128, manifest_version (+3 more)

### Community 29 - "fundo.js"
Cohesion: 0.33
Nodes (10): abasDe(), ciclo(), consultar(), escolher(), executar(), PERMITIDO, player, playerVivo() (+2 more)

### Community 31 - "requirements.txt (dependências Python)"
Cohesion: 0.20
Nodes (12): FastMCP("claudinho") transporte stdio, Reconhecimento da fala na nuvem (Groq) com volta pro Whisper, Tom da voz Microsoft (Thalita, Francisca, Antônio), Voz (Whisper + Piper, palavra de chamada), anthropic>=0.80, customtkinter>=5.2, requirements.txt (dependências Python), edge-tts>=7.0 (+4 more)

### Community 32 - "projetos.py"
Cohesion: 0.29
Nodes (7): abrir(), achar(), _dentro_das_liberadas(), eh_projeto(), _janela_do_projeto(), _pastas(), pastas_liberadas()

### Community 33 - "limpar"
Cohesion: 0.22
Nodes (3): _celulas(), limpar(), _tabela()

### Community 34 - "completar"
Cohesion: 0.16
Nodes (6): artista_de_rock(), comentar_musica(), comentar_tela(), tom_das_piadas(), completar(), ve_imagem()

### Community 35 - ".perguntar"
Cohesion: 0.20
Nodes (6): _completar_ollama(), frases_completas(), _imagens_ollama(), liberar_gpu_se_jogo(), _ollama(), _ollama_fluxo()

### Community 36 - "conversa.html"
Cohesion: 0.22
Nodes (7): /api/conversa endpoint, atualizar() polling /api/conversa, bolha(), Janela de conversa (conversa.html), markdown() conversor, Token X-Token (__TOKEN__), print_anexado

### Community 37 - "plano-ver-tela.md"
Cohesion: 0.25
Nodes (7): PROMPT_SISTEMA, ImageGrab + em_jpeg (~1280 px, JPEG 80), FERRAMENTAS (motores.py) com tool_result de imagem, ver_tela(alvo) ferramenta MCP, Faixa nos olhos (vendado), Personalidade (Claudinho / Ultron), Piadas sobre a tela

### Community 38 - ".__init__"
Cohesion: 0.12
Nodes (4): em_jpeg(), icone_enviar(), icone_mic(), paginar()

### Community 41 - "json"
Cohesion: 0.18
Nodes (6): main(), texto_de(), ultimos(), _ler(), _palavras(), Mini cérebro (SQLite FTS5 lembranças)

### Community 42 - "escrever_perfil"
Cohesion: 0.25
Nodes (3): escrever_perfil(), perfil_curto(), texto_do_mestre()

### Community 43 - "tela_cheia"
Cohesion: 0.29
Nodes (3): gpu_livre(), tela_cheia(), _vram_livre_mb()

### Community 44 - ".instalar_extensao"
Cohesion: 0.20
Nodes (3): caminho_do_navegador(), desenhar_icone(), montar_extensao()

### Community 46 - "motores.py"
Cohesion: 0.18
Nodes (11): ChatAPI, chave_api(), _cliente(), _completar_api(), _completar_claude_code(), env_limpo(), _pedido_api(), rodar_ajudante() (+3 more)

### Community 49 - "Claudinho (mascote de mesa)"
Cohesion: 0.32
Nodes (7): Plano: contexto de projeto (sessões do Claude Code) pro Júnior, AJUDANTE / ABRIR_NA_MAO (regex sobre comandos Bash), Plano: MCP exclusivo do Claudinho, Plano: Claudinho orquestrador + Júnior revisor visual, Plano: olha o que está na tela e me responde, Claudinho (mascote de mesa), MCP do Claudinho (abrir_programa)

### Community 50 - "ytmusic.js"
Cohesion: 0.83
Nodes (3): botao(), controle(), fazer()

### Community 51 - "Júnior revisor visual"
Cohesion: 0.29
Nodes (4): Júnior revisor visual, medir_cor, Modo Júnior (config modo_junior), pillow>=10.0

### Community 52 - "entrada"
Cohesion: 0.22
Nodes (3): entrada(), rotulo_atual(), montar()

### Community 53 - "--permission-prompt-tool stdio → responder_controle → pedir_permissao"
Cohesion: 0.29
Nodes (4): ChatClaude (processo do chat, flags), Ferramentas com confirmação (fechar_programa, copiar, rodar_script, criar_arquivo), --permission-prompt-tool stdio → responder_controle → pedir_permissao, Windows-MCP (genérico, não usar)

### Community 55 - "README.md · painel"
Cohesion: 0.67
Nodes (3): Painel (painel.html), ~/.claudinho/config.json, Painel de configurações (app do Edge InPrivate, API com token)

### Community 57 - "Módulo sessoes.py (listar, em_foco, uso)"
Cohesion: 0.33
Nodes (5): Claudecímetro (projeto antigo), Gasto de tokens da sessão, Registro de sessões ~/.claude/sessions/<pid>.json, Módulo sessoes.py (listar, em_foco, uso), Transcript ~/.claude/projects/<pasta>/<sessionId>.jsonl (message.usage)

### Community 59 - "desenhar() sprite no canvas"
Cohesion: 0.50
Nodes (5): animar(), corDoCorpo(), desenhar() sprite no canvas, hsv() arco-íris, pixelsDoAdereco()

### Community 65 - "Extensão do navegador (ext_token, polling 127.0.0.1)"
Cohesion: 0.40
Nodes (5): Modal de instalação da extensão, Consultar YouTube/YT Music via extensão (musica.py consultar/ir), Extensão do navegador (ext_token, polling 127.0.0.1), YouTube Music (ytmusicapi, rádio), ytmusicapi>=1.8

## Knowledge Gaps
- **25 isolated node(s):** `Mini cérebro (SQLite FTS5 lembranças)`, `voz_pausada em tela cheia`, `Ferramentas com confirmação (fechar_programa, copiar, rodar_script, criar_arquivo)`, `Windows-MCP (genérico, não usar)`, `/api/estado endpoint` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 373 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Claudinho` connect `Claudinho` to `Balao`, `.processar_eventos`, `.acao_menu`, `.comentar_do_banco`, `claudinho.pyw · comentários`, `.__init__`, `motores.py · chats`, `sistema.py`, `.area`, `disponivel`, `claudinho.pyw · servidor`, `.desenhar`, `limpar`, `completar`, `.__init__`, `.parecida`, `.mostrar`, `escrever_perfil`, `tela_cheia`, `.instalar_extensao`, `.tick`, `.animar_voz`, `entrada`, `.abrir_janela_web`, `.mostrar_estado_voz`?**
  _High betweenness centrality (0.289) - this node is a cross-community bridge._
- **What connects `Mini cérebro (SQLite FTS5 lembranças)`, `voz_pausada em tela cheia`, `Ferramentas com confirmação (fechar_programa, copiar, rodar_script, criar_arquivo)` to the rest of the system?**
  _25 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Fala` be split into smaller, more focused modules?**
  _Cohesion score 0.10752688172043011 - nodes in this community are weakly interconnected._
- **Why does `Voz` connect `Voz` to `voz.py`, `.__init__`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Should `musica.py · notificacoes.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06120218579234973 - nodes in this community are weakly interconnected._
- **Why does `Memoria` connect `memoria.py · Memoria` to `json`, `.__init__`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Should `frases.py · esquetes.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09269162210338681 - nodes in this community are weakly interconnected._