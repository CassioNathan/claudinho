"""Hooks "Stop" e "Notification" do Claude Code: avisam o Claudinho que um chat terminou de responder ou que
parou esperando você (pedindo permissão pra rodar algo, ou fazendo uma pergunta).

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


def main():
    if os.environ.get("CLAUDINHO_CHAT"):
        return  # é o próprio chat da Claudinho
    dados = json.loads(sys.stdin.buffer.read().decode("utf-8-sig", "replace") or "{}")
    dados = dados if isinstance(dados, dict) else {}
    cwd = dados.get("cwd") or ""
    projeto = Path(cwd).name or cwd
    if "scratch-" in projeto:
        projeto = "chat sem pasta"
    if dados.get("hook_event_name") == "Notification":
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
    corpo = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
    try:   # a chave que o Claudinho criou: sem ela ele recusa (qualquer programa poderia mandar aviso falso)
        chave = (DADOS / "aviso_token").read_text(encoding="utf-8").strip()
    except OSError:
        return
    req = urllib.request.Request(f"http://127.0.0.1:{PORTA}/aviso", data=corpo,
                                 headers={"Content-Type": "application/json", "X-Claudinho-Aviso": chave})
    urllib.request.urlopen(req, timeout=1.5)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
