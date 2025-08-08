from flask import Flask, request, jsonify
import requests

from common import *
from miner import Miner
from checker import *

PEERS = []

class Server:
    def __init__(self, port, blockchain, mine, my_id):
        self.app = Flask(__name__)
        self.blockchain = blockchain
        self.port = port

        self.miner = None
        if mine:
            self.miner = Miner(blockchain, my_id)

        @self.app.route("/share-job", methods=["POST"])
        def receive_job():
            if check_job(blockchain, request.get_json()["job_id"]).success:
                broadcast_peers(request.get_json(),"share-job", "Job") # spreading job to peers

            if not self.miner:
                return jsonify({"error": "Server is not a miner"}), 400
            data = request.get_json()
            prompt = data.get("prompt")
            seed = data.get("seed")
            model = data.get("model")
            if not prompt:
                return jsonify({"error": "No prompt provided"}), 400

            job = LLMJob(prompt=prompt,model=model, seed=seed)
            self.blockchain.add_job_to_mempool(job)
            self.miner.mine(job)
            return jsonify({"status": "job added", "job_id": job.job_id})
        

        @self.app.route("/share-block", methods=["POST"])
        def receive_block():
            data = request.get_json()
            # On reconstruit un bloc (simplifié pour MVP)
            new_block = Block.from_dict(data)

            success = blockchain.add_block(new_block)
            if success:
                share_block(new_block)
                return jsonify({"status": "ok"}), 200
            else:
                return jsonify({"error": "Block already exists"}), 202
            
        @self.app.route("/blockchain", methods=["GET"])
        def send_blockchain():
            print(info_c("Sharing blockchain"))
            return blockchain.to_dict(), 200

        @self.app.route("/balances", methods=["GET"])
        def get_balances():
            return jsonify(blockchain.balances), 200
        
        @self.app.route("/share-transaction", methods=["POST"])
        def receive_transaction():
            data = request.get_json()
            sender = data.get("sender")
            receiver = data.get("receiver")
            amount = data.get("amount")
            tx_id = data.get("tx_id")
            result = blockchain.process_transactions(sender, receiver, amount,share_transaction, tx_id)
            if result.success:
                print(success_c(f"Transaction received. Sender: {sender}, Receiver: {receiver}, Amount: {amount}"))
            else:
                print(warning_c(f"Transaction received but rejected. Error: {result.message}"))
            return result.message, result.code
            

        threading.Thread(target=self.start).start()
        time.sleep(0.5)

    def start(self):
        self.app.run(host="0.0.0.0", port=self.port)

def broadcast_peers(json_data,uri, elem):
    for peer in PEERS:
        try:
            res = requests.post(f"http://localhost:{peer}/{uri}", json=json_data)
            if res.status_code == 200:
                print(info_c(f"[+] {elem} sent to {peer}"))
            else:
                if res.status_code != 202:
                    print(error_c(f"[!] Error sending {elem} to {peer} : {res.status_code}"))
                
        except Exception as e:
            print(error_c(f"[!] Error connecting to peer {peer}: {e}"))

def share_block(block: Block):
    block_data = block.to_dict()
    broadcast_peers(block_data,"share-block", "Block")
    
def share_transaction(sender, receiver, amount, tx_id):
    transaction_data = {
        "sender": sender,
        "receiver": receiver,
        "amount": amount,
        "tx_id": tx_id
    }

    broadcast_peers(transaction_data,"share-transaction", "Transaction")

def submit_job(job: LLMJob):
    job_data = job.to_dict()

    broadcast_peers(job_data,"share-job", "Job")

def init_blockchain():
    try:
        blockchain = requests.get(f"http://localhost:{PEERS[0]}/blockchain").json()
        print(info_c("Blockchain received from peer:"), success_c(blockchain))
        return Blockchain().from_dict(blockchain)
    except Exception as e:
        if e.__class__.__name__ == "ConnectionError":
            print(error_c(f"[!] Impossible de communiquer avec le peer {PEERS[0]}"))
        else:
            raise f"[!] Erreur lors de la communication avec le peer {e}"
        return Blockchain()