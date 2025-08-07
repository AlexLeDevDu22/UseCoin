from flask import Flask, request, jsonify

from common import *
from miner import Miner

PEERS = []

class Server:
    def __init__(self, port, peers, blockchain, mine):
        self.app = Flask(__name__)
        self.blockchain = blockchain
        self.port = port

        self.miner = None
        if mine:
            self.miner = Miner(blockchain, str(uuid.uuid4()), self)

        @self.app.route("/submit-job", methods=["POST"])
        def submit_job():
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
        

        @self.app.route("/receive-block", methods=["POST"])
        def receive_block():
            data = request.get_json()
            # On reconstruit un bloc (simplifié pour MVP)
            try:
                dummy_job = LLMJob("external", seed=0)
                dummy_job.job_id = data["job_id"]
                dummy_job.prompt_hash = data["prompt_hash"]

                new_block = Block(
                    previous_hash=data["previous_hash"],
                    llm_job=dummy_job,
                    result=data["result_excerpt"],
                    result_hash=data["result_hash"],
                    miner_id=data["miner"]
                )
                new_block.timestamp = data["timestamp"]
                new_block.block_hash = data["block_hash"]

                success = blockchain.add_block(new_block)
                if success:
                    print("[✓] Bloc reçu et ajouté !")
                else:
                    print("[x] Bloc déjà existant ou invalide.")
                return jsonify({"status": "ok"}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 400
            
        @self.app.route("/blockchain", methods=["GET"])
        def send_blockchain():
            chain_data = []
            for block in self.blockchain.chain:
                chain_data.append({
                    "block_hash": block.block_hash,
                    "job_id": block.llm_job.job_id,
                    "result": block.result[:200],
                    "result_hash": block.result_hash,
                    "miner": block.miner_id,
                    "timestamp": block.timestamp,
                    "previous_hash": block.previous_hash
                })
            print("sending blockchain data: ", chain_data)
            return jsonify(chain_data)


        threading.Thread(target=self.start).start()
        time.sleep(0.5)

    def start(self):
        self.app.run(host="0.0.0.0", port=self.port)

def add_block(block: Block):
    block_data = {
        "timestamp": block.timestamp,
        "miner": block.miner_id,
        "job_id": block.llm_job.job_id,
        "prompt_hash": block.llm_job.prompt_hash,
        "result_hash": block.result_hash,
        "result_excerpt": block.result[:200],
        "block_hash": block.block_hash,
        "previous_hash": block.previous_hash
    }

    for peer in PEERS:
        try:
            res = requests.post(f"http://localhost:{peer}/receive-block", json=block_data)
            if res.status_code == 200:
                print(f"[+] Bloc envoyé à {peer}")
                return True
            else:
                print(f"[!] Erreur envoi à {peer} : {res.status_code}")
        except Exception as e:
            print(f"[!] Impossible d'envoyer à {peer} : {e}")
        return False
    
def init_blockchain():
    try:
        blockchain = requests.get(f"http://localhost:{PEERS[0]}/blockchain").json()
        print("blockchain received from peer:", blockchain)
        return Blockchain(blockchain)
    except Exception as e:
        if e.__class__.__name__ == "ConnectionError":
            print(f"[!] Impossible de communiquer avec le peer {PEERS[0]}")
        else:
            raise f"[!] Erreur lors de la communication avec le peer {e}"
        return Blockchain()