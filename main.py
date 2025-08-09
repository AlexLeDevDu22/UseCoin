# === UseCoin MVP Stage 2 ===
# Objectif :
# - Simulation d'une mempool contenant plusieurs jobs
# - Plusieurs mineurs concurrents
# - Construction d'une blockchain chaînée
# - Seul le premier mineur à traiter un job est récompensé

import argparse

from protocole import *
import prompter
import network
import PoUW

# --- INITIALISATION ---
parser = argparse.ArgumentParser(description="UseCoin: miner ou prompter")
parser.add_argument("mode", choices=["miner", "prompter", "transaction", "blockchain", "balances", "peers", "my-id", "mempool", "hash-mempool"], help="Mode d'exécution")
parser.add_argument("--port", type=int, required=True, help="Port du noeud courant")
parser.add_argument("--peers", nargs="*", type=int, default=[], help="Liste des ports des autres noeuds")
parser.add_argument("--amount", type=float, help="Montant pour une transaction")
parser.add_argument("--receiver", type=str, help="Id du destinataire pour une transaction")
parser.add_argument("--data-path", type=str, default="data.json", help="Chemin vers le fichier de données")

args = parser.parse_args()

data_path = args.data_path
with open(data_path, "r") as f:
    DATA = json.load(f)
if not DATA.get("my_id"):
    DATA["my_id"] = str(uuid.uuid4())
    with open(data_path, "w") as f:
        json.dump(DATA, f)

my_id = DATA["my_id"]

network.PEERS = args.peers
blockchain = network.init_blockchain()
blockchain.init_balances()

# --- SIMULATION ---

match args.mode:
    case "prompter":
        server = network.Server(args.port, blockchain, mine=False, my_id=my_id, result_callback=prompter.result_callback)

        prompter.call(blockchain, my_id)

    case "miner":
        server = network.Server(args.port, blockchain, mine=True, my_id=my_id)

    case "transaction":
        if args.amount is None:
            parser.error("--amount est requis en mode transaction")
        if args.receiver is None:
            parser.error("--receiver est requis en mode transaction")

        blockchain.process_transactions(my_id, args.receiver, args.amount, network.share_transaction)

    case "blockchain":
        print(info_c("Affichage de la blockchain :"))
        for i, block in enumerate(blockchain.chain):
            print(success_c(f"Bloc Number {i}: {block.block_hash}, Miner: {block.miner_id}"))
        print("\n")

    case "balances":
        print(info_c("Affichage des comptes :"))
        for balance in blockchain.balances.items():
            if balance[0] == my_id:
                print(success_c(f"Wallet {balance[0]}: {balance[1]} UCO"))
            else:
                print(info_c(f"Wallet {balance[0]}: {balance[1]} UCO"))
        print("\n")
    case "mempool":
        print(info_c("Affichage de la mempool :"))
        for tx in blockchain.mempool["transactions"]:
            print(success_c(f"Transaction {tx.tx_id}"))
        for job in blockchain.mempool["jobs"]:
            print(success_c(f"Job {job.job_id}"))
        print("\n")

    case "peers":
        print(info_c("Affichage des peers :"))
        for peer in args.peers:
            print(success_c(f"Peer {peer}"))
        print("\n")

    case "my-id":
        print(success_c(f"Votre id : {my_id}"))
        print("\n")

    case "hash-mempool":
        print(info_c("Hash de la mempool :"))
        timestamp = time.time()
        difficulty = PoUW.difficulty
        print(success_c(blockchain.compute_hash_mempool(timestamp, my_id, difficulty)))
        print("\n")