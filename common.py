import hashlib
import uuid
import time
import threading
import configparser
import requests

# --- CONFIGURATION ---
config = configparser.ConfigParser()
config.read('config.ini')

# --- STRUCTURES ---
class LLMJob:
    def __init__(self, prompt, model=config["TEST"]["OLLAMA_MODEL"], seed=42):
        self.job_id = str(uuid.uuid4())
        self.prompt = prompt
        self.model = model
        self.seed = seed
        self.prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        self.claimed = False

class Block:
    def __init__(self, previous_hash=None, llm_job=None, result=None, result_hash=None, miner_id=None):
        self.timestamp = time.time()
        self.previous_hash = previous_hash
        self.llm_job = llm_job
        self.result = result
        self.result_hash = result_hash
        self.miner_id = miner_id
        self.block_hash = self.compute_hash()

    def compute_hash(self):
        if None not in [self.timestamp, self.previous_hash, self.llm_job, self.result_hash, self.miner_id]:
            block_content = f"{self.timestamp}{self.previous_hash}{self.llm_job.job_id}{self.result_hash}{self.miner_id}"
            return hashlib.sha256(block_content.encode()).hexdigest()
        return None
    
    def parse_json(self, json):
        self.timestamp = json["timestamp"]
        self.previous_hash = json["previous_hash"]
        self.llm_job = LLMJob(json["job_id"])
        self.result = json["result"]
        self.result_hash = json["result_hash"]
        self.miner_id = json["miner"]
        self.block_hash = json["block_hash"]
        return self

# --- BLOCKCHAIN ---
class Blockchain:
    def __init__(self, init_chain: list=[]):
        self.lock = threading.Lock()
        self.chain = []
        for block in init_chain:
            block_ = Block().parse_json(block)
            self.add_block(block_)

        self.mempool = []
        if len(self.chain) == 0:
            self.init_genesis_block()


    def init_genesis_block(self):
        genesis_job = LLMJob("Genesis block")
        block = Block("0" * 64, genesis_job, "Genesis result", hashlib.sha256(b"Genesis result").hexdigest(), "GENESIS")
        self.chain.append(block)

    def add_block(self, block):
        with self.lock:
            # Check if job already processed
            for b in self.chain:
                if b.llm_job.job_id == block.llm_job.job_id:
                    return False
            self.chain.append(block)
            return True

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