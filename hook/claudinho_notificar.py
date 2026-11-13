"""Hooks do Claude Code que contam ao Claudinho (que é o próprio Claude Code do PC, com cara de mascote) o que cada
chat está fazendo:

- Stop: terminou de responder; Notification: parou esperando você;
- SessionStart / SessionEnd / UserPromptSubmit / PreToolUse (assíncronos, não atrasam o chat): a lista viva de
  sessões (o que estou fazendo em cada janela);
- PermissionRequest: o pedido de permissão vai pro balão do Claudinho e ESPERA a sua resposta lá (Pode/Não). Sem o
  Claudinho aberto, sem resposta a tempo ou com "no app", não decide nada e o pedido aparece normal no chat. A
  pergunta com opções (AskUserQuestion) também: você escolhe no balão e a resposta volta pro chat;
- Stop, depois do aviso: espera um pouco você responder pelo balão (texto ou voz). Respondeu: o chat continua com a
  sua mensagem (decision "block" + reason). Não respondeu: termina normal. A regra do tempo está no responder.py.

Lê o JSON do hook pelo stdin, pega o último pedido e a última resposta do
transcript e manda para http://127.0.0.1:47821. Se a Claudinho não estiver
aberta, não faz nada. Nunca bloqueia nem quebra o Claude Code.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

PORTA = 47821
DADOS = Path(os.environ.get("CLAUDINHO_DADOS") or Path.home() / ".claudinho")


def texto_de(conteudo):
    if isinstance(conteudo, str):
        return conteudo
    if isinstance(conteudo, list):
        partes = [b.get("text", "") for b in conteudo
                  if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(p for p in partes if p)
    return ""


EDITORES = ("Edit", "MultiEdit", "Write", "NotebookEdit")


def ultimos(transcript):
    """Último pedido digitado, última resposta em texto e os arquivos que o chat mexeu desde o pedido
    (lendo só o fim do arquivo)."""
    pedido = resposta = ""
    mexeu = []
    try:
        with open(transcript, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 3_000_000))
            linhas = f.read().decode("utf-8-sig", "replace").splitlines()
    except Exception:
        return pedido, resposta, mexeu
    for linha in reversed(linhas):
        try:
            item = json.loads(linha)
        except Exception:
            continue
        msg = item.get("message") or {}
        if item.get("type") == "assistant":
            if not resposta:
                resposta = texto_de(msg.get("content")).strip()
            if not pedido:   # ainda dentro da última rodada: anota o que ele editou ou criou
                for b in msg.get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in EDITORES:
                        entrada = b.get("input") if isinstance(b.get("input"), dict) else {}
                        arq = entrada.get("file_path") or entrada.get("notebook_path")
                        if isinstance(arq, str) and arq and arq not in mexeu:
                            mexeu.append(arq)
        elif not pedido and item.get("type") == "user" and not item.get("isMeta"):
            t = texto_de(msg.get("content")).strip()
            if t and not t.startswith("<"):
                pedido = t
        if pedido and resposta:
            break
    return pedido, resposta, mexeu[:30]


# Notification que vale avisar: a sessão travou esperando você. O "idle_prompt" (parado esperando a próxima
# mensagem) não entra: quando termina, o aviso do Stop já veio
ESPERANDO = ("permission_prompt", "elicitation_dialog")


def esperando_voce(dados):
    tipo = dados.get("notification_type")
    if tipo:
        return tipo in ESPERANDO
    mensagem = str(dados.get("message") or "").lower()   # versão do Claude Code que não manda o tipo
    return "permission" in mensagem or "needs your" in mensagem


# da entrada da ferramenta só vai o que diz O QUE ela faz (nada de conteúdo de arquivo)
CAMPOS_LEVES = ("description", "file_path", "notebook_path", "path", "pattern", "url", "query", "subagent_type")
CAMPOS_PERMISSAO = CAMPOS_LEVES + ("command", "old_string", "new_string", "content", "prompt", "action", "text")
# pedido de permissão que não dá pra responder com Pode/Não nem com opções (aprovar plano): fica no chat
SO_NO_CHAT = ("ExitPlanMode",)
PERGUNTA = "AskUserQuestion"
ESPERA_PERMISSAO_S = 100   # quanto o hook espera sua resposta no balão (o timeout dele no settings é maior)
ESPERA_RESPOSTA_S = 900    # responder/escolher pelo balão (quem decide o tempo de verdade é o Claudinho)


def leve(entrada, campos=CAMPOS_LEVES, limite=300):
    entrada = entrada if isinstance(entrada, dict) else {}
    return {k: str(entrada[k])[:limite] for k in campos if entrada.get(k) not in (None, "")}


def enviar(caminho, corpo, espera=1.5):
    """POST no Claudinho com a chave dele. Devolve o corpo da resposta (ou None: ele não está aberto)."""
    try:   # a chave que o Claudinho criou: sem ela ele recusa (qualquer programa poderia mandar aviso falso)
        chave = (DADOS / "aviso_token").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    req = urllib.request.Request(f"http://127.0.0.1:{PORTA}{caminho}",
                                 data=json.dumps(corpo, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json", "X-Claudinho-Aviso": chave})
    with urllib.request.urlopen(req, timeout=espera) as r:
        return r.read()


def pedir_permissao(dados, base):
    """PermissionRequest: o balão do Claudinho decide. Imprime a decisão pro Claude Code (ou nada)."""
    ferramenta = dados.get("tool_name") or ""
    if ferramenta in SO_NO_CHAT:
        return
    entrada = dados.get("tool_input") if isinstance(dados.get("tool_input"), dict) else {}
    corpo = dict(base, ferramenta=ferramenta, entrada=leve(entrada, CAMPOS_PERMISSAO, 2000))
    if ferramenta == PERGUNTA:
        perguntas = entrada.get("questions")
        if not isinstance(perguntas, list) or not perguntas:
            return
        corpo["perguntas"] = perguntas
    try:
        resposta = json.loads(enviar("/permissao", corpo, espera=(ESPERA_RESPOSTA_S if ferramenta == PERGUNTA
                                                                  else ESPERA_PERMISSAO_S) + 5) or b"{}")
    except Exception:
        return
    decisao = resposta.get("decisao")
    if ferramenta == PERGUNTA:   # escolheu no balão: a pergunta já vai respondida (as respostas por texto da pergunta)
        respostas = resposta.get("respostas")
        if decisao != "allow" or not isinstance(respostas, dict) or not respostas:
            return
        saida = {"behavior": "allow", "updatedInput": dict(entrada, answers=respostas)}
    elif decisao == "allow":
        saida = {"behavior": "allow"}
    elif decisao == "deny":
        saida = {"behavior": "deny", "message": "O usuário disse não pelo Claudinho."}
    else:
        return   # sem resposta ou "no app": o pedido aparece normal no chat
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": saida}}))


def esperar_resposta(corpo):
    """Stop: o aviso vai e fica esperando você responder pelo balão. Respondeu: o chat continua com a sua mensagem."""
    try:
        resposta = json.loads(enviar("/resposta", corpo, espera=ESPERA_RESPOSTA_S) or b"{}")
    except Exception:
        return
    texto = str(resposta.get("texto") or "").strip()
    if texto:
        print(json.dumps({"decision": "block", "reason": "Mensagem do usuário, mandada pelo balão do Claudinho: "
                                                          + texto}))


def main():
    if os.environ.get("CLAUDINHO_CHAT"):
        return  # é o próprio chat da Claudinho
    dados = json.loads(sys.stdin.buffer.read().decode("utf-8-sig", "replace") or "{}")
    dados = dados if isinstance(dados, dict) else {}
    cwd = dados.get("cwd") or ""
    projeto = Path(cwd).name or cwd
    if "scratch-" in projeto:
        projeto = "chat sem pasta"
    evento = dados.get("hook_event_name")
    base = {"projeto": projeto, "pasta": cwd, "session_id": dados.get("session_id")}
    if evento == "PermissionRequest":
        return pedir_permissao(dados, base)
    if evento in ("SessionStart", "SessionEnd", "UserPromptSubmit", "PreToolUse"):
        if evento == "SessionStart":
            corpo = dict(base, evento="inicio")
        elif evento == "SessionEnd":
            corpo = dict(base, evento="fechou")
        elif evento == "UserPromptSubmit":
            corpo = dict(base, evento="pedido", pedido=str(dados.get("prompt") or "")[:1000])
        else:
            corpo = dict(base, evento="ferramenta", ferramenta=dados.get("tool_name"), entrada=leve(dados.get("tool_input")))
        try:
            enviar("/aviso", corpo)
        except Exception:
            pass
        return
    if evento == "Notification":
        if not esperando_voce(dados):
            return
        corpo = {"evento": "espera", "projeto": projeto, "pasta": cwd, "session_id": dados.get("session_id"),
                 "mensagem": str(dados.get("message") or "")[:500], "tipo": dados.get("notification_type")}
    else:
        pedido, resposta, mexeu = ultimos(dados.get("transcript_path", ""))
        resposta = dados.get("last_assistant_message") or resposta
        corpo = {
            "projeto": projeto,
            "pasta": cwd,
            "pedido": pedido[:1000],
            "resposta": resposta[:6000],
            "session_id": dados.get("session_id"),
            "mexeu": mexeu,
        }
    if evento == "Stop":
        return esperar_resposta(corpo)   # (o /resposta também dá o aviso)
    enviar("/aviso", corpo)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
