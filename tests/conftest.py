"""Os testes rodam com uma pasta de dados temporária (nunca o ~/.claudinho de verdade) e importam os módulos da raiz."""
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
os.environ["CLAUDINHO_DADOS"] = tempfile.mkdtemp(prefix="claudinho_teste_")
for pasta in (RAIZ, RAIZ / "hook", RAIZ / "treino_voz"):
    sys.path.insert(0, str(pasta))
