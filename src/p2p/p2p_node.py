import os
import socket
import struct
import threading
import time
import hashlib
from src.chat_utils.chat_message import ChatMessage
from src.chat_utils.chat_history import ChatHistory

PORT = 51511
PEER_REQUEST = 0x1
PEER_LIST = 0x2
ARCHIVE_REQUEST = 0x3
ARCHIVE_RESPONSE = 0x4

def recv_all(conn, length):
    buf = b''
    while len(buf) < length:
        data = conn.recv(length - len(buf))
        if not data:
            raise ConnectionError("Socket connection broken")
        buf += data
    return buf

class P2PNode:
    def __init__(self, ip, known_peer=None):
        self.ip = ip
        self.known_peer = known_peer
        self.peers = {ip} 
        self.lock = threading.Lock()
        self.history = ChatHistory()
        self.active_connections = set()

    def start(self):
        threading.Thread(target=self.listen_for_peers, daemon=True).start()
        if self.known_peer:
            self.connect_to_peer(self.known_peer)
        
        threading.Thread(target=self.send_periodic_peer_requests, daemon=True).start()

    def listen_for_peers(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.ip, PORT))
        server.listen()
        print(f"Escutando por conexões em {self.ip}:{PORT}")

        while True:
            conn, addr = server.accept()
            print(f"Conexão aceita de {addr[0]}")
            threading.Thread(target=self.handle_peer, args=(conn, addr), daemon=True).start()
    
    def handle_peer(self, conn, addr):
        peer_ip = addr[0]
        print(f"Conexão estabelecida com {peer_ip}. Iniciando handler.")
        
        with self.lock:
            if peer_ip not in self.peers:
                print(f"\nNovo par descoberto pela conexão: {peer_ip} \n")
            
            self.peers.add(peer_ip)
            self.active_connections.add(peer_ip)
        try:
            while True:
                msg_type_byte = recv_all(conn, 1)
                msg_type = struct.unpack("!B", msg_type_byte)[0]

                if msg_type == PEER_REQUEST:
                    print(f"[{peer_ip}] => PeerRequest recebido")
                    self.send_peer_list(conn)
                elif msg_type == PEER_LIST:
                    print(f"[{peer_ip}] => PeerList recebido")
                    self.handle_peer_list(conn)
                elif msg_type == ARCHIVE_REQUEST:
                    print(f"[{peer_ip}] => ArchiveRequest recebido")
                    self.send_archive_response(conn)
                elif msg_type == ARCHIVE_RESPONSE:
                    print(f"[{peer_ip}] => ArchiveResponse recebido")
                    self.handle_archive_response(conn)
                else:
                    print(f"[{peer_ip}] Mensagem desconhecida: {msg_type}")
                    break 
        except (ConnectionError, struct.error) as e:
            print(f"Conexão com {peer_ip} perdida: {e}")
        finally:
            with self.lock:
                if peer_ip in self.active_connections:
                    self.active_connections.remove(peer_ip)
            conn.close()
            print(f"Conexão com {peer_ip} foi fechada.")

    def send_peer_list(self, conn):
        with self.lock: 
            peers_list = list(self.peers)

        data = struct.pack("!BI", PEER_LIST, len(peers_list))
        for ip_str in peers_list:
            ip_bytes = socket.inet_aton(ip_str)
            data += ip_bytes
        conn.sendall(data)
        print(">> PeerList enviada")

    def handle_peer_list(self, conn):
        n_peers_bytes = recv_all(conn, 4)
        n = struct.unpack("!I", n_peers_bytes)[0]
        
        for _ in range(n):
            ip_bytes = recv_all(conn, 4)
            ip_str = socket.inet_ntoa(ip_bytes)
            
            with self.lock:
                if ip_str not in self.peers:
                    print(f">> Novo par descoberto: {ip_str}")
                    self.peers.add(ip_str)

    def connect_to_peer(self, peer_ip):
        if peer_ip == self.ip:
            return

        with self.lock:
            if peer_ip in self.active_connections:
                return
        
        try:
            print(f">> Tentando conectar ao par {peer_ip}...")
            sock = socket.create_connection((peer_ip, PORT), timeout=5)
            
            sock.settimeout(None) 

            threading.Thread(target=self.handle_peer, args=(sock, (peer_ip, PORT)), daemon=True).start()
            
            sock.sendall(struct.pack("!B", PEER_REQUEST))

        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            print(f"Falha ao conectar com {peer_ip}: {e}")
            with self.lock:
                if peer_ip in self.peers:
                    self.peers.remove(peer_ip)


    def send_periodic_peer_requests(self):
        while True:
            time.sleep(10)
            
            with self.lock:
                other_peers = self.peers - {self.ip}  
                peers_to_check = list(other_peers - self.active_connections)

            if peers_to_check:
                print(f"Verificando conexões com {len(peers_to_check)} pares inativos: {peers_to_check}")
            
            for peer_ip in peers_to_check:
                self.connect_to_peer(peer_ip)

    def send_archive_response(self, conn):
        data = self.history.serialize()
        conn.sendall(data)
        print(">> ArchiveResponse enviado")
    
    def handle_archive_response(self, conn):
        print(">> Recebendo ArchiveResponse...")
        header = recv_all(conn, 4) 
        c = struct.unpack("!I", header)[0]
        print(f">> Histórico recebido tem {c} mensagens. Deserializando...")
        
        current_payload = b''
        try:
            for i in range(c):
                n_byte = recv_all(conn, 1) 
                n = struct.unpack("!B", n_byte)[0]
                chat_data = recv_all(conn, n + 32) 
                current_payload += n_byte + chat_data
            
            full_message = struct.pack("!BI", ARCHIVE_RESPONSE, c) + current_payload

            new_history = ChatHistory()
            new_history.deserialize(full_message)

            print(">> Validação do novo histórico...")
            if new_history.is_valid():
                if len(new_history.messages) > len(self.history.messages):
                    print("Histórico novo é maior e válido. Atualizando.")
                    self.history = new_history
                else:
                    print(">> Histórico válido, mas não é maior que o atual. Ignorando.")
            else:
                print("Histórico recebido é inválido. Ignorando.")

        except (ConnectionError, struct.error) as e:
            print(f"Erro ao processar ArchiveResponse: {e}")

    def mine_and_add_chat(self, message_text):
        print(f">> Mineração iniciada para a mensagem: '{message_text}'")
        base_chats = self.history.messages[-19:]
        
        new_chat = ChatMessage(message_text) 

        while True:
            verifier = os.urandom(16)
            new_chat.verifier = verifier
            
            temp_history_chats = base_chats + [new_chat]
            data_to_hash = b''.join([m.serialize() for m in temp_history_chats])
            data_to_hash = data_to_hash[:-16]  

            md5 = hashlib.md5(data_to_hash).digest()

            if md5.startswith(b'\x00\x00'):
                new_chat.md5 = md5
                print(f"Chat minerado! Hash: {md5.hex()}")
                self.history.messages.append(new_chat)
                print(">> Disseminando novo histórico para a rede...")
                self.broadcast_new_history()
                break

    def broadcast_new_history(self):
        with self.lock:
            peers_to_broadcast = list(self.peers)
        
        serialized_history = self.history.serialize()

        for peer_ip in peers_to_broadcast:
            if peer_ip == self.ip:
                continue
            try:
                sock = socket.create_connection((peer_ip, PORT), timeout=5)
                sock.sendall(serialized_history)
                print(f">> Histórico enviado para {peer_ip}")
                sock.close()
            except Exception as e:
                print(f">> Falha ao enviar histórico para {peer_ip}: {e}")

    def print_history(self):
        print("\n" + "="*60)
        print(" HISTÓRICO DE CHAT ATUAL")
        print("="*60)

        messages_copy = list(self.history.messages)
        
        if not messages_copy:
            print("O histórico está vazio.")
        else:
            print(f"Total de mensagens na blockchain: {len(messages_copy)}\n")
            for i, msg in enumerate(messages_copy):
                text = msg.text.decode('ascii', errors='ignore')
                md5_hex = msg.md5.hex()
                
                print(f"--- Mensagem {i} ---")
                print(f"  Texto: {text}")
                print(f"  Hash : {md5_hex}")
        
        print("="*60 + "\n")

    def print_peers(self):
        """Imprime a lista de pares conhecidos."""
        print("\n" + "-"*30)
        print(" Pares Conhecidos na Rede")
        print("-"*30)
        with self.lock: 
            peers_copy = list(self.peers)
            if not peers_copy:
                print("Nenhum par conhecido.")
            else:
                print(f"Total: {len(peers_copy)}")
                for peer_ip in peers_copy:
                    is_self = " (Este nó)" if peer_ip == self.ip else ""
                    print(f"  - {peer_ip}{is_self}")
        print("-"*30 + "\n")
