from protocole import *
from crypting import encrypt_job_result
import PoUW

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
        
    def mine(self, job: LLMJob, blockchain: Blockchain):
        print(info_c(f"[Miner {self.my_id}] Traitement du job: {job.job_id}..."))
        result = self.execute_llm_job(job)
        print(success_c(f"[Miner {self.my_id}] Résultat obtenu: {result[:200]}..."))

        job.crypted_response = encrypt_job_result(result, job.public_key)
        job.miner_id = self.my_id
        timestamp = time.time()
        job.response_timestamp = timestamp

        if check_job(self.blockchain, job).success:
            network.share_job(self.blockchain, job)
            self.blockchain.mempool["jobs"].append(job)

            if PoUW.reward_job(self.blockchain, self.my_id, timestamp):
                print("JOB REWARDED!!!!!!!!")
                network.block_validation(blockchain, job)

            return job