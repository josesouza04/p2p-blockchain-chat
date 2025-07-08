import struct
import os

class ChatMessage:
    def __init__(self, text, verifier=None, md5=None):
        self.text = text.encode('ascii')
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
        n = struct.unpack("!B", data[0:1])[0]
        text = data[1:1 + n].decode('ascii')
        verifier = data[1 + n:1 + n + 16]
        md5 = data[1 + n + 16:1 + n + 32]
        return ChatMessage(text, verifier, md5), 1 + n + 32
