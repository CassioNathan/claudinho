"""Servidor MCP do Claudinho: uma ferramenta só, abrir qualquer programa instalado no PC.

Não abre site, não roda comando, não passa argumento, não fecha nada: só abre (ou traz pra frente) o programa
que o usuário pediu pelo nome ("Claudinho, abre a Steam"), mesmo que ele esteja fechado, minimizado ou na bandeja.
O chat do Claudinho liga esse servidor sozinho (stdio); pra testar na mão:  python claudinho_mcp.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.mcpserver import MCPServer

import programas

servidor = MCPServer("claudinho", instructions="Abre programas instalados no PC do usuário, só isso.")


@servidor.tool()
def abrir_programa(nome: str) -> str:
    """Abre um programa instalado no PC pelo nome (aproximado: 'steam', 'vscode', 'bloco de notas', 'discord').
    Se o programa já estiver aberto, minimizado ou rodando em segundo plano, traz a janela dele pra frente.
    Não aceita argumentos nem comandos, só o nome do programa."""
    try:
        return programas.abrir(nome[:80])
    except Exception as e:
        return f"não consegui abrir: {e}"


if __name__ == "__main__":
    servidor.run()
