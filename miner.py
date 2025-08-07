from common import *
import ollama
import network

class Miner:
    def __init__(self, blockchain: Blockchain, miner_id: str, server):
        self.blockchain = blockchain
        self.miner_id = miner_id
        self.server = server

    def execute_llm_job(self, job: LLMJob) -> str:
        """
        Exécute un job LLM via la librairie Python Ollama.
        """
        try:
            response = ollama.generate(
                model=job.model,
                prompt=job.prompt,
                options={
                    "seed": job.seed,
                    "num_predict": int(config["TEST"]["MAX_TOKENS"]),
                }
            )
            return response['response'].strip()
        except Exception as e:
            return f"[ERROR] LLM execution failed: {e}"
        
    def mine(self, job: LLMJob):
        print(f"[Miner {self.miner_id}] Traitement du job: {job.job_id}...")
        result = self.execute_llm_job(job)
        print(f"[Miner {self.miner_id}] Résultat obtenu: {result[:200]}...")
        result_hash = hashlib.sha256(result.encode()).hexdigest()
        block = Block(self.blockchain.get_last_hash(), job, result[:200], result_hash, self.miner_id)
        success = self.blockchain.add_block(block)
        if success:
            resuccess = network.add_block(block)
            if resuccess:
                print(f"[Miner {self.miner_id}] Bloc ajouté à la blockchain: {block.block_hash}\n")
            else:
                print(f"[Miner {self.miner_id}] Bloc rejeté (job déjà traité).")
        else:
            print(f"[Miner {self.miner_id}] Job déjà traité. Bloc rejeté.\n")
            