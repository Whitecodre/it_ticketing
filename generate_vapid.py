# generate_vapid.py
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import base64

def generate_vapid_keys():
    # Generate private key (P-256 curve)
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()

    # Serialize private key to PEM format (with headers)
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    # Serialize public key as raw uncompressed point (65 bytes)
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    # Base64url encode public key
    public_key_b64 = base64.urlsafe_b64encode(public_bytes).decode('utf-8').rstrip('=')

    # Base64url encode private key (PEM string -> base64)
    private_key_b64 = base64.urlsafe_b64encode(pem_private.encode('utf-8')).decode('utf-8').rstrip('=')

    return {
        'public_key': public_key_b64,
        'private_key': private_key_b64,
        'private_key_pem': pem_private,
    }

if __name__ == '__main__':
    keys = generate_vapid_keys()
    print("Add these to your .env file:")
    print()
    print(f"VAPID_PUBLIC_KEY={keys['public_key']}")
    print(f"VAPID_PRIVATE_KEY={keys['private_key']}")
    print()
    print("Alternatively, you can store the private key as PEM (multi-line) if you prefer:")
    print(keys['private_key_pem'])