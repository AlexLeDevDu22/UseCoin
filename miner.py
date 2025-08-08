from common import *

import ollama
import network

class Miner:
    def __init__(self, blockchain: Blockchain, my_id: str):
        self.blockchain = blockchain
        self.my_id = my_id

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
        print(info_c(f"[Miner {self.my_id}] Traitement du job: {job.job_id}..."))
        result = self.execute_llm_job(job)
        print(success_c(f"[Miner {self.my_id}] Résultat obtenu: {result[:200]}..."))
        result_hash = hashlib.sha256(result.encode()).hexdigest()
        block = Block(self.blockchain.get_last_hash(), job, result[:200], result_hash, self.my_id, [])
        
        success = self.blockchain.add_block(block)
        print(success_c(f"[Miner {self.my_id}] Bloc ajouté à la blockchain: {block.block_hash}\n"))
        if success:
            resuccess = network.share_block(block)
            if resuccess:
                print(success_c(f"[Miner {self.my_id}] Bloc partagé: {block.block_hash}\n"))
            else:
                print(error_c(f"[Miner {self.my_id}] Bloc rejeté."))
        else:
            print(error_c(f"[Miner {self.my_id}] Job déjà traité. Bloc rejeté.\n"))
            