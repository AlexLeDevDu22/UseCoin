import hashlib
import uuid
import time
import threading
import configparser
import json

from checker import *

# --- CONFIGURATION ---
config = configparser.ConfigParser()
config.read('config.ini')

# --- STRUCTURES ---
class LLMJob:
    def __init__(self, prompt, model=config["TEST"]["OLLAMA_MODEL"], seed=None, client_id=None, claimed=False, job_id=None, prompt_hash=None):
        self.job_id = job_id or str(uuid.uuid4())
        self.prompt = prompt
        self.model = model
        self.seed = seed
        self.prompt_hash = prompt_hash or hashlib.sha256(prompt.encode()).hexdigest()
        self.claimed = claimed
        self.client_id = client_id

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "prompt": self.prompt,
            "model": self.model,
            "seed": self.seed,
            "prompt_hash": self.prompt_hash,
            "claimed": self.claimed,
            "client_id": self.client_id
        }

class Block:
    def __init__(self, previous_hash=None, llm_job=None, result=None, result_hash=None, miner_id=None, transactions=[]):
        self.timestamp = time.time()
        self.previous_hash = previous_hash
        self.llm_job = llm_job
        self.result = result
        self.result_hash = result_hash
        self.miner_id = miner_id
        self.transactions = transactions
        self.block_hash = self.compute_hash()

    @classmethod
    def from_dict(cls, data):
        # Reconstruire le LLMJob du bloc
        llm_job = LLMJob(**data["llm_job"]) if isinstance(data["llm_job"], dict) else data["llm_job"]
        # Reconstruire les transactions
        transactions = [Transaction.from_dict(tx) for tx in data.get("transactions", [])]
        block = cls(
            previous_hash=data.get("previous_hash"),
            llm_job=llm_job,
            result=data.get("result"),
            result_hash=data.get("result_hash"),
            miner_id=data.get("miner_id"),
            transactions=transactions
        )
        block.timestamp = data.get("timestamp", time.time())
        block.block_hash = data.get("block_hash")
        return block
    
    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "llm_job": vars(self.llm_job),  # ou self.llm_job.to_dict() si tu ajoutes cette méthode
            "result": self.result,
            "result_hash": self.result_hash,
            "miner_id": self.miner_id,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "block_hash": self.block_hash
        }

    def compute_hash(self):
        if None not in [self.timestamp, self.previous_hash, self.llm_job, self.result_hash, self.miner_id, self.transactions]:
            block_string = json.dumps({
                "timestamp": self.timestamp,
                "prompt_hash": self.llm_job.prompt_hash,
                "result_hash": self.result_hash,
                "previous_hash": self.previous_hash,
                "miner_id": self.miner_id,
                "transactions": [tx.to_dict() for tx in self.transactions]
            }, sort_keys=True).encode()
            return hashlib.sha256(block_string).hexdigest()
        return None
        
    
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
        self.mempool = []
        self.balances = {}  # wallet_id -> UCO balance
        if len(self.chain) == 0:
            self.init_genesis_block()

    @classmethod
    def from_dict(cls, data):
        
        blockchain = cls()
        # Reconstruire la chaîne de blocs
        blockchain.chain = [Block.from_dict(b) for b in data.get("chain", [])]
        # Reconstruire la mempool
        blockchain.mempool = [LLMJob(**j) for j in data.get("mempool", [])]
        # Reconstruire les soldes
        blockchain.balances = data.get("balances", {})
        # Reconstrauire les transactions
        blockchain.transactions = [Transaction.from_dict(tx) for tx in data.get("transactions", [])]

        return blockchain
    
    def to_dict(self):
        return {
            "chain": [block.to_dict() for block in self.chain],
            "mempool": [vars(job) for job in self.mempool],  # ou job.to_dict() si tu ajoutes cette méthode à LLMJob
            "balances": self.balances
        }

    def init_genesis_block(self):
        genesis_job = LLMJob("Genesis block")
        block = Block("0" * 64, genesis_job, "Genesis result", hashlib.sha256(b"Genesis result").hexdigest(), "GENESIS", [])
        self.chain.append(block)

    def add_block(self, block):
        with self.lock:
            # Check if job already processed
            for b in self.chain:
                if b.llm_job.job_id == block.llm_job.job_id:
                    return False
            self.chain.append(block)
            print(success_c(f"[✓] Bloc num {len(self.chain)} ajouté avec succès: {block.block_hash}"))
            self.reward_miner(block.miner_id)

            return True

    def get_last_block(self):
        return self.chain[-1]

    def get_last_hash(self):
        return self.chain[-1].block_hash

    def add_job_to_mempool(self, job):
        self.mempool.append(job)

    def fetch_unclaimed_job(self):
        with self.lock:
            for job in self.mempool:
                if not job.claimed:
                    job.claimed = True
                    return job
        return None
    
    def reward_miner(self, miner_id):
        self.balances[miner_id] = self.balances.get(miner_id, 0) + int(config["TEST"]["REWARD_AMOUNT"])

    def init_transactions(self):
        for block in self.chain:
            for tx in block.transactions:
                self.balances[tx.sender] = self.balances.get(tx.sender, 0) - tx.amount
                self.balances[tx.receiver] = self.balances.get(tx.receiver, 0) + tx.amount

    def process_transactions(self, sender, receiver, amount, share_transaction_funct, tx_id=str(uuid.uuid4())):
        checking = check_transaction(self, sender, receiver, amount, tx_id)
        if checking.success:
            print(success_c(f"Transaction accepted. Sender: {sender}, Receiver: {receiver}, Amount: {amount}"))
            self.get_last_block().transactions.append(Transaction(sender, receiver, amount, tx_id))
            self.balances[sender] = self.balances.get(sender, 0) - amount
            self.balances[receiver] = self.balances.get(receiver, 0) + amount

            share_transaction_funct(sender, receiver, amount, tx_id)
        else:
            if checking.code != 202:
                print(warning_c(f"Transaction rejected. Error: {checking.message}"))
        return checking



# LOGS UTILS
def error_c(text):
    return f"\033[91m{text}\033[00m" # red
def success_c(text):
    return f"\033[94m{text}\033[00m" # green
def info_c(text):
    return f"\033[92m{text}\033[00m" # blue
def warning_c(text):
    return f"\033[93m{text}\033[00m" # yellow