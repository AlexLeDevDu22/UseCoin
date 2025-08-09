from protocole import *

class CheckingResult:
    def __init__(self, success: bool, message: str = "",http_json: dict = {}, code: int = 200):
        self.success = success
        self.message = message
        self.http_json = http_json
        self.code = code

def check_transaction(blockchain, sender, receiver, amount, tx_id) -> CheckingResult:

    if not sender or not receiver or not amount:
        return CheckingResult(False, "Invalid transaction data", {}, 400)
    
    if amount <= 0:
        return CheckingResult(False, "Invalid transaction amount", {}, 400)
    
    if blockchain.balances.get(sender, 0) < amount:
        return CheckingResult(False, "Insufficient balance", {}, 400)
    
    for tx in blockchain.get_last_block().transactions:
        if tx.tx_id == tx_id:
            return CheckingResult(False, "Transaction already exists", {}, 202) # transaction already processed

    return CheckingResult(True, "Transaction Processed", {}, 200)

def check_job(blockchain, job) -> CheckingResult:

    for job_ in blockchain.mempool["jobs"]:
        if job_.job_id == job.job_id and (job_.crypted_response or not job.crypted_response):
            return CheckingResult(False, "Job already processed", {}, 202)
    
    if job.crypted_response and job.response_timestamp < blockchain.get_last_block().timestamp:
        return CheckingResult(False, "Job too old", {}, 400)
    
    for block in blockchain.chain:
        for job_ in block.jobs:
            if job_.job_id == job.job_id:
                return CheckingResult(False, "Job already processed", {}, 202)
        
    if job.prompt == "":
        return CheckingResult(False, "No prompt provided", {}, 400)
        
    return CheckingResult(True, "Job Processed", {}, 200)

def check_block(blockchain, block) -> CheckingResult:

    # check if already exist
    for block_ in blockchain.chain:
        if block_.block_hash == block.block_hash:
            return CheckingResult(False, "Block already processed", {}, 202)
    
    return CheckingResult(True, "Block Processed", {}, 200)