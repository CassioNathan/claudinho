"""Hook "Stop" do Claude Code: avisa a Claudinho que um chat terminou de responder.

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


def texto_de(conteudo):
    if isinstance(conteudo, str):
        return conteudo
    if isinstance(conteudo, list):
        partes = [b.get("text", "") for b in conteudo
                  if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(p for p in partes if p)
    return ""


def ultimos(transcript):
    """Último pedido digitado e última resposta em texto, lendo só o fim do arquivo."""
    pedido = resposta = ""
    try:
        with open(transcript, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 3_000_000))
            linhas = f.read().decode("utf-8-sig", "replace").splitlines()
    except Exception:
        return pedido, resposta
    for linha in reversed(linhas):
        try:
            item = json.loads(linha)
        except Exception:
            continue
        msg = item.get("message") or {}
        if not resposta and item.get("type") == "assistant":
            resposta = texto_de(msg.get("content")).strip()
        elif not pedido and item.get("type") == "user" and not item.get("isMeta"):
            t = texto_de(msg.get("content")).strip()
            if t and not t.startswith("<"):
                pedido = t
        if pedido and resposta:
            break
    return pedido, resposta


def main():
    if os.environ.get("CLAUDINHO_CHAT"):
        return  # é o próprio chat da Claudinho
    dados = json.loads(sys.stdin.buffer.read().decode("utf-8-sig", "replace") or "{}")
    pedido, resposta = ultimos(dados.get("transcript_path", ""))
    resposta = dados.get("last_assistant_message") or resposta
    cwd = dados.get("cwd") or ""
    projeto = Path(cwd).name or cwd
    if "scratch-" in projeto:
        projeto = "chat sem pasta"
    corpo = json.dumps({
        "projeto": projeto,
        "pasta": cwd,
        "pedido": pedido[:1000],
        "resposta": resposta[:4000],
        "session_id": dados.get("session_id"),
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(f"http://127.0.0.1:{PORTA}/aviso", data=corpo,
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=1.5)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
