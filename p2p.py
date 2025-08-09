import requests
import socket

BOOTSTRAP_NODE = "https://ton-noeud-central.exemple.com:5000"  # change ça si t'as un serveur public
LOCAL_PORT = 5001  # ou le port local de ton node actuel

def get_public_ip():
    try:
        return requests.get("https://api.ipify.org").text
    except:
        return None

def register_with_bootstrap():
    public_ip = get_public_ip()
    if not public_ip:
        print("[x] Impossible d’obtenir l’IP publique.")
        return
    my_url = f"http://{public_ip}:{LOCAL_PORT}"
    try:
        res = requests.post(f"{BOOTSTRAP_NODE}/peers", json={"peer": my_url})
        if res.status_code == 200:
            print(f"[✓] Enregistré auprès du noeud bootstrap : {my_url}")
    except Exception as e:
        print(f"[x] Échec enregistrement bootstrap : {e}")

if __name__ == "__main__":
    register_with_bootstrap()
