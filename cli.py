"""Ajudante de linha de comando do Claudinho (empacotado vira claudinho-cli.exe, com console).

    claudinho-cli musica <ação> [...]   o mesmo que python musica.py (o chat usa pra música e YouTube)
    claudinho-cli abrir <ação> [...]    o mesmo que python abrir.py (abrir site, pesquisa, programa)
    claudinho-cli mcp                   o servidor MCP do Claudinho (uma ferramenta: abrir programa)
    claudinho-cli aviso                 o hook "Stop" do Claude Code (lê o JSON no stdin e avisa o Claudinho)

Existe pra ninguém precisar ter Python instalado: o Claudinho empacotado chama este exe.
"""
import sys


def main():
    for fluxo in (sys.stdout, sys.stderr):  # acentos e ♪ saem certinho pro chat
        if fluxo is not None and hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2 or sys.argv[1] not in ("musica", "abrir", "aviso", "mcp"):
        sys.exit(__doc__)
    qual = sys.argv[1]
    sys.argv = [f"{sys.argv[0]} {qual}"] + sys.argv[2:]
    if qual == "musica":
        import musica
        musica.main()
    elif qual == "abrir":
        import abrir
        abrir.main()
    elif qual == "mcp":
        import claudinho_mcp
        claudinho_mcp.servidor.run()
    else:
        import claudinho_notificar  # nunca pode quebrar nem travar o Claude Code
        try:
            claudinho_notificar.main()
        except Exception:
            pass


if __name__ == "__main__":
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent / "hook"))
    main()
