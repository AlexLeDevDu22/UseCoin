# === UseCoin MVP Stage 2 ===
# Objectif :
# - Simulation d'une mempool contenant plusieurs jobs
# - Plusieurs mineurs concurrents
# - Construction d'une blockchain chaînée
# - Seul le premier mineur à traiter un job est récompensé

import argparse

from common import *
import prompter
import network


# --- INITIALISATION ---
parser = argparse.ArgumentParser(description="UseCoin: miner ou prompter")
parser.add_argument("mode", choices=["miner", "prompter", "transaction"], help="Mode d'exécution")
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
blockchain.init_transactions()

# --- SIMULATION ---
server = network.Server(args.port, blockchain, mine=(args.mode == "miner"), my_id=my_id)

if args.mode == "prompter":
    prompter.main(blockchain, peers=args.peers, my_id=my_id)
elif args.mode == "transaction":
    if args.amount is None:
        parser.error("--amount est requis en mode transaction")
    if args.receiver is None:
        parser.error("--receiver est requis en mode transaction")

    blockchain.process_transactions(my_id, args.receiver, args.amount, network.share_transaction)

