import struct
import hashlib
from src.chat_utils.chat_message import ChatMessage

class ChatHistory:
    def __init__(self):
        self.messages = []

    def serialize(self):
        payload = b''.join([m.serialize() for m in self.messages])
        return struct.pack("!BI", 0x4, len(self.messages)) + payload

    def deserialize(self, data):
        c = struct.unpack("!I", data[1:5])[0]
        i = 5
        self.messages = []
        for _ in range(c):
            msg, size = ChatMessage.deserialize(data[i:])
            self.messages.append(msg)
            i += size

    def is_valid(self):
        return self._validate_recursive(self.messages)

    def _validate_recursive(self, msgs):
        if len(msgs) == 0:
            return True
        if len(msgs) == 1:
            return self._check_md5(msgs)

        return self._validate_recursive(msgs[:-1]) and self._check_md5(msgs)

    def _check_md5(self, msgs):
        last = msgs[-1]
        data = b''.join([m.serialize() for m in msgs[-20:]])
        data = data[:-16] 

        h = hashlib.md5(data).digest()
        return h[:2] == b'\x00\x00' and h == last.md5
