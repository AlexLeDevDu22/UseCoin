from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import os
import base64


def generate_key_pair():
    # Générer une clé privée RSA 2048 bits
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Extraire la clé publique à partir de la clé privée
    public_key = private_key.public_key()

    # Exporter en PEM (format standard texte)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,  # standard format
        encryption_algorithm=serialization.NoEncryption()
    )

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return private_pem.decode(), public_pem.decode()


def encrypt_job_result(result: str, public_key_pem: str):
    # Charger la clé publique
    public_key = serialization.load_pem_public_key(public_key_pem.encode())

    # Générer une clé AES aléatoire
    aes_key = os.urandom(32)  # AES-256

    # Chiffrer le message avec AES
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(aes_key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(result.encode()) + encryptor.finalize()

    # Chiffrer la clé AES avec RSA
    encrypted_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    # Retourne tout encodé en base64
    return {
        "encrypted_key": base64.b64encode(encrypted_key).decode(),
        "iv": base64.b64encode(iv).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode()
    }

def decrypt_job_result(encrypted_dict: dict, private_key_pem: str) -> str:
    # 1. Déchiffrer la clé AES
    encrypted_key = base64.b64decode(encrypted_dict["encrypted_key"])
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode(),
        password=None
    )
    aes_key = private_key.decrypt(
        encrypted_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    # 2. Déchiffrer le message avec AES
    iv = base64.b64decode(encrypted_dict["iv"])
    ciphertext = base64.b64decode(encrypted_dict["ciphertext"])
    cipher = Cipher(algorithms.AES(aes_key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(ciphertext) + decryptor.finalize()
    return decrypted.decode()
