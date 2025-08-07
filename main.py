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
parser.add_argument("mode", choices=["miner", "prompter"], help="Mode d'exécution")
parser.add_argument("--port", type=int, required=True, help="Port du noeud courant")
parser.add_argument("--peers", nargs="*", type=int, default=[], help="Liste des ports des autres noeuds")
args = parser.parse_args()

network.PEERS = args.peers
blockchain = network.init_blockchain()
server = network.Server(args.port, args.peers, blockchain, mine=(args.mode == "miner"))

# --- SIMULATION ---
if args.mode == "prompter":
    prompter.main(blockchain, peers=args.peers)
