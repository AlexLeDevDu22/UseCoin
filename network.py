from flask import Flask, request, jsonify
import requests
import copy

from protocole import *
from miner import Miner
from checker import *

PEERS = []

class Server:
    def __init__(self, port, blockchain, mine, my_id, result_callback=None):
        self.app = Flask(__name__)
        self.blockchain = blockchain
        self.port = port
        self.result_callback = result_callback

        self.miner = None
        if mine:
            self.miner = Miner(blockchain, my_id)

        @self.app.route("/share-job", methods=["POST"])
        def receive_job():
            job = LLMJob(**request.get_json())
            checking = check_job(blockchain, job)
            if checking:
                blockchain.mempool["jobs"].append(copy.deepcopy(job))
                share_job(blockchain, job)# spreading job to peers

                if job.client_id == my_id and job.crypted_response: # response to me
                    self.result_callback(job)
                    return jsonify({"status": "ok"}), 200

                if not self.miner:
                    return jsonify({"error": "Server is not a miner"}), 400
                
                threading.Thread(target=self.miner.mine, args=(job, blockchain)).start()
                return jsonify({"status": "ok"}), 200

            return jsonify({"error": f"Error: "+checking.message}), checking.code
            
        @self.app.route("/blockchain", methods=["GET"])
        def send_blockchain():
            print(info_c("Sharing blockchain"))
            return blockchain.to_dict(), 200
        
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
        
        @self.app.route("/block-validation", methods=["POST"])
        def receive_block_validation():
            data = request.get_json()
            block = Block.from_dict(data)
            checking = check_block(blockchain, block)

            if checking.success:
                blockchain.add_block(block)
                share_block(block)
                return jsonify({"status": "ok"}), 200
            else:
                return jsonify(checking.http_json), checking.code
            

        threading.Thread(target=self.start).start()
        time.sleep(0.5)

    def start(self):
        self.app.run(host="0.0.0.0", port=self.port)

def broadcast_peers(json_data,uri, elem):
    for peer in PEERS:
        try:
            print(info_c(f"[+] {elem} sent to {peer}"))
            res = requests.post(f"http://localhost:{peer}/{uri}", json=json_data)
            if res.status_code not in [200, 202]:
                print(error_c(f"[!] Error sending {elem} to {peer} : {res.text}(http: {res.status_code})"))
                
        except Exception as e:
            print(error_c(f"[!] Error connecting to peer {peer}: {e}"))
            PEERS.remove(peer)

def share_block(block: Block):
    block_data = block.to_dict()
    broadcast_peers(block_data,"block-validation", "Block")
    
def share_transaction(sender, receiver, amount, tx_id):
    transaction_data = {
        "sender": sender,
        "receiver": receiver,
        "amount": amount,
        "tx_id": tx_id
    }

    broadcast_peers(transaction_data,"share-transaction", "Transaction")

def share_job(blockchain: Blockchain, job: LLMJob):
    checking = check_job(blockchain, job)
    if checking.success:
        for job_ in blockchain.mempool["jobs"]:
            if job_.job_id == job.job_id:
                blockchain.mempool["jobs"].remove(job_)
        blockchain.mempool["jobs"].append(job)
        job_data = job.to_dict()
        broadcast_peers(job_data,"share-job", "Job")
    else:
        if checking.code != 202:
            print(error_c("Error submitting job: "+  checking.message))

def init_blockchain():    
    try:
        blockchain = requests.get(f"http://localhost:{PEERS[0]}/blockchain").json()
        # print(info_c("Blockchain received from peer:"), success_c(blockchain))
        return Blockchain().from_dict(blockchain)
    except Exception as e:
        if e.__class__.__name__ == "ConnectionError":
            print(error_c(f"[!] Impossible de communiquer avec le peer {PEERS[0]}"))
        else:
            raise f"[!] Erreur lors de la communication avec le peer {e}"
        return Blockchain()
    
def block_validation(blockchain, job: LLMJob):
    new_block = Block(blockchain.get_last_hash(), 
                      blockchain.mempool["jobs"], 
                      job.miner_id, 
                      blockchain.mempool["transactions"],
                      job.response_timestamp
                      )
    checking = check_block(blockchain, new_block)
    if checking.success:
        blockchain.add_block(new_block)
        share_block(new_block)
    else:
        print(error_c("Error validating block: "+  checking.message))