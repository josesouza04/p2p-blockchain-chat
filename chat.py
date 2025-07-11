import sys
import time
from src.p2p.p2p_node import P2PNode

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python chat.py <ip_local> [ip_conhecido]")
        sys.exit(1)

    ip_local = sys.argv[1]
    known_peer = sys.argv[2] if len(sys.argv) > 2 else None

    node = P2PNode(ip_local, known_peer)
    node.start()
    time.sleep(1)

    print("\n___P2P Blockchain Chat iniciado___")
    print("Digite uma mensagem para enviar para a rede.")
    print("Comandos auxiliares:")
    print("  /history -> Para ver o histórico de mensagens.")
    print("  /peers   -> Para ver a lista de pares conhecidos.")
    print("Use Ctrl+C para sair.\n")

    while True:
        try:
            msg = input("> ")
            
            if not msg:
                continue

            command = msg.lower()

            if command == '/history':
                node.print_history()
            elif command == '/peers':
                node.print_peers()
            else:
                node.mine_and_add_chat(msg)

        except (KeyboardInterrupt, EOFError):
            print("\nSaindo...")
            break