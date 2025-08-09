from protocole import *
from network import share_job
from crypting import *

private_key, public_key = generate_key_pair()

def call(blockchain: Blockchain, my_id):
    prompt = input("Entrez votre prompt : ")
    
    job = LLMJob(prompt, my_id, public_key)
    
    share_job(blockchain, job)

def result_callback(job: LLMJob):
    response = decrypt_job_result(job.crypted_response, private_key)

    print(success_c(response))