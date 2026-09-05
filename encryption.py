import os
import base64
import hashlib

from cryptography.fernet import Fernet


def generate_key(password):
    """
    Generate a Fernet-compatible key from the user's password.
    """
    password_hash = hashlib.sha256(
        password.encode("utf-8")
    ).digest()

    return base64.urlsafe_b64encode(password_hash)


def encrypt_file(file_data, password):
    """
    Encrypt file data using the password.
    """
    key = generate_key(password)

    cipher = Fernet(key)

    encrypted_data = cipher.encrypt(file_data)

    return encrypted_data


def decrypt_file(encrypted_data, password):
    """
    Decrypt encrypted file data using the password.
    """
    key = generate_key(password)

    cipher = Fernet(key)

    decrypted_data = cipher.decrypt(encrypted_data)

    return decrypted_data