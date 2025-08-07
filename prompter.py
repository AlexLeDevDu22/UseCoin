from common import *

def main(blockchain: Blockchain, peers: list):
    prompt = input("Entrez votre prompt : ")
    if prompt == "/blockchain":
        print("Affichage de la blockchain :")
        for block in blockchain.chain:
            print(f"Bloc {block.block_hash} - Job ID: {block.llm_job.job_id} - Résultat: {block.result[:50]}...")
        return
    job = LLMJob(prompt=prompt)
    blockchain.add_job_to_mempool(job)

    payload = {
        "prompt": prompt,
        "model": config["TEST"]["OLLAMA_MODEL"],
        "seed": uuid.uuid4().int  # Génération d'un seed aléatoire
    }
    for peer in peers:
        try:
            requests.post(f"http://localhost:{peer}/submit-job", json=payload)
        except Exception as e:
            print(f"[ERROR] Envoi du job au peer {peer} échoué: {e}")
    print(f"Prompt ajouté à la mempool avec l'id {job.job_id}")