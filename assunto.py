"""Linha de raciocínio: um assunto por vez. Depois da última coisa do assunto (sua mensagem, a resposta, um aviso,
um botão), por ASSUNTO_S segundos ele não puxa outro assunto sozinho (piada, comentário de música, esquete, pausa)."""
import time

ASSUNTO_S = 240


class Assunto:
    def __init__(self):
        self.ate = 0.0   # até quando tem assunto em andamento

    def marcar(self, falas=None, agora=None):
        """Renova o silêncio. Piada e comentário à toa que estavam na fila (`falas`) saem: chegariam no meio dele."""
        self.ate = (time.time() if agora is None else agora) + ASSUNTO_S
        if falas is not None:
            for papo in [f for f in falas if f.get("piada")]:
                falas.remove(papo)

    def ativo(self, ocupado=False, entrada=False, agora=None):
        return bool(ocupado or entrada) or (time.time() if agora is None else agora) < self.ate
