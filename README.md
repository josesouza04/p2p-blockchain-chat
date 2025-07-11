# P2P Blockchain Chat

Trabalho da disciplina de **Redes de Computadores (DCC/UFMG)** — 2025/1

## Descrição

Este projeto implementa um sistema de **chat distribuído P2P** com **verificação de histórico via Blockchain simplificado**, utilizando `hashes MD5`.

A arquitetura segue o padrão peer-to-peer, onde os nós descobrem uns aos outros, trocam mensagens e mantêm um histórico verificável.

---

## Execução

Requisitos:

- Python

### Instruções

1. Clone ou descompacte o projeto:
   ```bash
   unzip p2p-blockchain-chat.zip
   cd p2p-blockchain-chat
   ```
2. Execute um nó passando o IP Local:
    ```bash
    python3 chat.py 127.0.0.1
    ```
3. Conecte a outro peer:
    ```bash
    python3 chat.py 127.0.0.1 <IP_DO_PEER>
    ```

### Comandos Internos
* /history → Mostra o histórico de mensagens.
* /peers → Lista os pares conhecidos.

## Validação Via BlockChain
Cada mensagem é serializada e possui um hash MD5 calculado sobre as últimas 20 mensagens. O hash precisa começar com dois bytes nulos (0x0000).

O histórico é validado recursivamente e só é aceito se for válido e maior que o atual.
