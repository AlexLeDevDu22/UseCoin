import hashlib
import uuid
import time
import threading
import configparser
import json

from checker import *
from PoUW import *

# --- CONFIGURATION ---
config = configparser.ConfigParser()
config.read('config.ini')

# --- STRUCTURES ---
class LLMJob:
    def __init__(self, prompt, client_id, public_key, model=config["TEST"]["OLLAMA_MODEL"], seed=uuid.uuid4().int, claimed=False, job_id=str(uuid.uuid4()), crypted_response=None, miner_id=None, response_timestamp=None):
        self.job_id = job_id
        self.prompt = prompt
        self.model = model
        self.seed = seed
        self.claimed = claimed
        self.client_id = client_id
        self.public_key = public_key
        self.crypted_response = crypted_response
        self.response_timestamp = response_timestamp
        self.miner_id = miner_id

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "prompt": self.prompt,
            "model": self.model,
            "seed": self.seed,
            "claimed": self.claimed,
            "client_id": self.client_id,
            "public_key": self.public_key,
            "crypted_response": self.crypted_response,
            "response_timestamp": self.response_timestamp,
            "miner_id": self.miner_id
        }

class Block:
    def __init__(self, previous_hash, jobs, miner_id, transactions, timestamp, block_hash=None):
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.jobs = jobs  # list of LLMJob
        self.miner_id = miner_id
        self.transactions = transactions
        self.block_hash = block_hash or self.compute_hash()

    @classmethod
    def from_dict(cls, data):
        # Reconstruire le LLMJob du bloc
        jobs = [LLMJob(**job) for job in data["jobs"]]
        # Reconstruire les transactions
        transactions = [Transaction.from_dict(tx) for tx in data.get("transactions", [])]
        block = cls(
            previous_hash=data.get("previous_hash"),
            jobs=jobs,
            miner_id=data.get("miner_id"),
            transactions=transactions,
            block_hash=data.get("block_hash"),
            timestamp = data.get("timestamp")
        )
        return block
    
    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "jobs": [job.to_dict() for job in self.jobs],
            "miner_id": self.miner_id,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "block_hash": self.block_hash
        }
    
    def compute_hash(self):
        hash_dict = {
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "jobs": [job.to_dict() for job in self.jobs],
            "miner_id": self.miner_id,
            "transactions": [tx.to_dict() for tx in self.transactions]
        }
        block_string = json.dumps(hash_dict, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

class Transaction:
    def __init__(self, sender, receiver, amount, tx_id):
        self.tx_id = tx_id
        self.sender = sender
        self.receiver = receiver
        self.amount = amount

    @classmethod
    def from_dict(cls, data):
        tx = cls(
            tx_id=data.get("tx_id"),
            sender=data.get("sender"),
            receiver=data.get("receiver"),
            amount=data.get("amount")
        )
        tx.tx_id = data.get("tx_id", str(uuid.uuid4()))
        return tx

    def to_dict(self):
        return {
            "tx_id": self.tx_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount
        }

# --- BLOCKCHAIN ---
class Blockchain:
    def __init__(self):
        self.lock = threading.Lock()
        self.chain = []
        self.mempool = {"transactions": [], "jobs": []}
        self.balances = {}  # wallet_id -> UCO balance
        if len(self.chain) == 0:
            self.init_genesis_block()

    @classmethod
    def from_dict(cls, data):
        
        blockchain = cls()
        # Reconstruire la chaîne de blocs
        blockchain.chain = [Block.from_dict(b) for b in data.get("chain", [])]
        # Reconstruire la mempool
        blockchain.mempool["transactions"] = [Transaction.from_dict(tx) for tx in data["mempool"]["transactions"]]
        blockchain.mempool["jobs"] = [LLMJob(**j) for j in data["mempool"]["jobs"]]
        # Reconstruire les soldess
        blockchain.balances = data.get("balances", {})
        # Reconstrauire les transactions
        blockchain.transactions = [Transaction.from_dict(tx) for tx in data.get("transactions", [])]

        return blockchain
    
    def to_dict(self):
        return {
            "chain": [block.to_dict() for block in self.chain],
            "mempool": {
                "transactions": [tx.to_dict() for tx in self.mempool["transactions"]],
                "jobs": [job.to_dict() for job in self.mempool["jobs"]]
            },
            "balances": self.balances
        }

    def init_genesis_block(self):
        block = Block("0" * 64, [], "GENESIS", [], time.time())
        self.chain.append(block)

    def add_block(self, block):
        with self.lock:
            self.chain.append(block)
            self.empty_mempool()
            print(success_c(f"[✓] Bloc num {len(self.chain)} ajouté avec succès: {block.block_hash}"))
            self.reward_miner(block.miner_id)
            if len(self.chain) % config["TEST"]["DIFF_ADJUST_INTERVAL"] == 0:
                adjust_difficulty(self)

            return True

    def get_last_block(self):
        return self.chain[-1]

    def get_last_hash(self):
        return self.chain[-1].block_hash

    def fetch_unclaimed_job(self):
        with self.lock:
            for job in self.mempool:
                if not job.claimed:
                    job.claimed = True
                    return job
        return None
    
    def empty_mempool(self):
        self.mempool["transactions"] = []
        self.mempool["jobs"] = []
    
    def reward_miner(self, miner_id):
        print(success_c(f"[✓] Rewarding miner {miner_id}"))
        self.balances[miner_id] = self.balances.get(miner_id, 0) + int(config["TEST"]["REWARD_AMOUNT"])

    def init_balances(self):
        for block in self.chain:
            for tx in block.transactions:
                self.balances[tx.sender] = self.balances.get(tx.sender, 0) - tx.amount
                self.balances[tx.receiver] = self.balances.get(tx.receiver, 0) + tx.amount

    def process_transactions(self, sender, receiver, amount, share_transaction_funct, tx_id=str(uuid.uuid4())):
        checking = check_transaction(self, sender, receiver, amount, tx_id)
        if checking.success:
            print(success_c(f"Transaction accepted. Sender: {sender}, Receiver: {receiver}, Amount: {amount}"))
            self.mempool["transactions"].append(Transaction(sender, receiver, amount, tx_id))
            self.balances[sender] = self.balances.get(sender, 0) - amount
            self.balances[receiver] = self.balances.get(receiver, 0) + amount

            share_transaction_funct(sender, receiver, amount, tx_id)
        else:
            if checking.code != 202:
                print(warning_c(f"Transaction rejected. Error: {checking.message}"))
        return checking
    
    def compute_hash_mempool(self, timestamp, miner_id, difficulty):
        mempool_ = {
            "previous_hash": self.get_last_hash(),
            "timestamp": timestamp,
            "miner_id": miner_id,
            "difficulty": difficulty,
            "transactions": [tx.to_dict() for tx in self.mempool["transactions"]],
            "jobs": [job.to_dict() for job in self.mempool["jobs"]]
        }
        block_string = json.dumps(mempool_, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
        

# LOGS UTILS
def error_c(text):
    return f"\033[91m{text}\033[00m" # red
def success_c(text):
    return f"\033[94m{text}\033[00m" # green
def info_c(text):
    return f"\033[92m{text}\033[00m" # blue
def warning_c(text):
    return f"\033[93m{text}\033[00m" # yellow