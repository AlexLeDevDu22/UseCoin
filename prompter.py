from common import *
import network

def main(blockchain: Blockchain, peers: list, my_id):
    while True:
        prompt = input("Entrez votre prompt : ")
        match prompt:
            case "/blockchain":
                print(info_c("Affichage de la blockchain :"))
                for block in blockchain.chain:
                    print(success_c(f"Bloc {block.block_hash} - Job ID: {block.llm_job.job_id} - Résultat: {block.result[:50]}..."))
                print("\n")
                continue
            case "/balances":
                print(info_c("Affichage des comptes :"))
                for balance in blockchain.balances.items():
                    if balance[0] == my_id:
                        print(success_c(f"Wallet {balance[0]}: {balance[1]} UCO"))
                    else:
                        print(info_c(f"Wallet {balance[0]}: {balance[1]} UCO"))
                print("\n")
                continue
            case "/peers":
                print(info_c("Affichage des peers :"))
                for peer in peers:
                    print(success_c(f"Peer {peer}"))
                print("\n")
                continue
            case "/my-id":
                print(info_c(f"Votre id : {my_id}"))
                print("\n")
                continue
        
        job = LLMJob(prompt=prompt)
        blockchain.add_job_to_mempool(job)

        network.submit_job(job)