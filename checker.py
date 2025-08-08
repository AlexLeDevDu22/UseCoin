from common import *

class CheckingResult:
    def __init__(self, success: bool, message: str = "",http_json: dict = {}, code: int = 200):
        self.success = success
        self.message = message
        self.http_json = http_json
        self.code = code

def check_transaction(blockchain, sender, receiver, amount, tx_id):

    if not sender or not receiver or not amount:
        return CheckingResult(False, "Invalid transaction data", {}, 400)
    
    if blockchain.balances.get(sender, 0) < amount:
        return CheckingResult(False, "Insufficient balance", {}, 400)
    
    for tx in blockchain.get_last_block().transactions:
        if tx.tx_id == tx_id:
            return CheckingResult(False, "Transaction already exists", {}, 202) # transaction already processed

    return CheckingResult(True, "Transaction Processed", {}, 200)

def check_job(blockchain, job_id):
    for block in blockchain.chain:
        if block.llm_job.job_id == job_id:
            return CheckingResult(False, "Job already processed", {}, 202)
        
    for job in blockchain.mempool:
        if job.job_id == job_id:
            return CheckingResult(False, "Job already processed", {}, 202)
        
    return CheckingResult(True, "Job Processed", {}, 200)