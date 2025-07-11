import struct
import os

class ChatMessage:
    def __init__(self, text_content, verifier=None, md5=None):
        if isinstance(text_content, str):
            self.text = text_content.encode('ascii', errors='replace')
        else:
            self.text = text_content

        self.n = len(self.text)
        self.verifier = verifier or os.urandom(16)
        self.md5 = md5 or b'\x00' * 16

    def serialize(self):
        return (
            struct.pack("!B", self.n)
            + self.text
            + self.verifier
            + self.md5
        )

    @staticmethod
    def deserialize(data):
        if len(data) < 1:
            raise ValueError("Dados insuficientes para deserializar o tamanho do texto.")
        
        n = struct.unpack("!B", data[0:1])[0]
        
        if len(data) < 1 + n + 32:
            raise ValueError("Dados insuficientes para o payload da mensagem.")

        text_bytes = data[1:1 + n]
        
        verifier = data[1 + n:1 + n + 16]
        md5 = data[1 + n + 16:1 + n + 32]
        
        return ChatMessage(text_bytes, verifier, md5), 1 + n + 32