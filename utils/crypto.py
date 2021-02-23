
import os
import binascii
import hmac
import hashlib
from pbkdf2 import PBKDF2
from Crypto.Cipher import AES
from struct import pack, unpack

def md5(s: str) :
    return hashlib.md5(s.encode('utf-8')).hexdigest()

def random_bytes(length) :
    bytes = os.urandom(length)
    return bytes

def random_bytes_str(length) :
    return binascii.hexlify(bytearray(random_bytes(length))).decode()

def AES_Encrypt(key, plaintext, salt) :
    iv = random_bytes(16)
    if isinstance(key, str) :
        kdf = PBKDF2(key, salt)
        key = kdf.read(32)
        key_mac = kdf.read(32)
    else :
        kdf = PBKDF2(key, salt)
        key_mac = kdf.read(32)
    mac = hmac.new(key_mac, digestmod = hashlib.md5)
    mac.update(iv)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    data_len = len(plaintext)
    if data_len % 16 != 0 :
        plaintext += b'\0' * ( 16 - ( data_len % 16 ) )
    encrypted = cipher.encrypt(plaintext)
    mac.update(encrypted)

    return iv + pack('<q', data_len) + mac.digest() + encrypted

def AES_Decrypt(key, ciphertext, salt) :
    if isinstance(key, str) :
        kdf = PBKDF2(key, salt)
        key = kdf.read(32)
        key_mac = kdf.read(32)
    else :
        kdf = PBKDF2(key, salt)
        key_mac = kdf.read(32)
    iv = ciphertext[:16]
    data_len, = unpack('<q', ciphertext[16:16+8])
    mac_correct = ciphertext[16+8:16+8+16]
    encrypted_data = ciphertext[16+8+16:]

    mac = hmac.new(key_mac, digestmod = hashlib.md5)
    mac.update(iv)
    mac.update(encrypted_data)
    mac_calculated = mac.digest()

    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(encrypted_data)

    if data_len % 16 != 0 :
        decrypted = decrypted[ : -( 16 - ( data_len % 16 ) ) ]

    return mac_correct == mac_calculated, decrypted

def generate_user_crypto_PBKDF2(password) :
    salt1 = random_bytes(16)
    salt2 = random_bytes(16)
    password_hashed = PBKDF2(password, salt1).read(32)
    master_key = random_bytes(32)
    master_key_encrypted = AES_Encrypt(password, master_key, salt2)
    return 'PBKDF2', password_hashed, salt1, salt2, master_key_encrypted

def verify_password_PBKDF2(password, salt1, password_hashed) :
    password_hashed_calc = PBKDF2(password, salt1).read(32)
    return password_hashed_calc == password_hashed

def update_crypto_PBKDF2(old_password, new_password, salt2, master_key_encrypted) :
    if old_password is None :
        return update_crypto_PBKDF2_password_only(new_password, salt2, master_key_encrypted)
    ret, master_key = AES_Decrypt(old_password, master_key_encrypted, salt2)
    salt1 = random_bytes(16)
    salt2 = random_bytes(16)
    password_hashed = PBKDF2(new_password, salt1).read(32)
    master_key_encrypted = AES_Encrypt(new_password, master_key, salt2)
    return 'PBKDF2', password_hashed, salt1, salt2, master_key_encrypted

def update_crypto_PBKDF2_password_only(new_password, salt2, master_key_encrypted) :
    salt1 = random_bytes(16)
    salt2 = random_bytes(16)
    password_hashed = PBKDF2(new_password, salt1).read(32)
    return 'PBKDF2', password_hashed, salt1, salt2, master_key_encrypted

if __name__ == "__main__":
    key = '123'
    text = b'abc'
    salt = random_bytes(16)
    encrypted = AES_Encrypt(key ,text, salt)
    decrypted = AES_Decrypt(key, encrypted, salt)
    print(text, decrypted)
