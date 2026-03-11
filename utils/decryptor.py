"""
decryptor.py
────────────────────────────────────────────────────────
helper:// encrypted URLs ko decrypt karta hai.
Key/IV Saini-txt repo se liya gaya hai.
────────────────────────────────────────────────────────
"""

import re
from base64 import b64decode
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from config import Config


def decrypt_url(enc_url: str) -> str:
    """
    helper://XXXXX  →  actual https://... URL
    """
    try:
        enc_url = enc_url.replace("helper://", "").strip()
        cipher  = AES.new(Config.AES_KEY, AES.MODE_CBC, Config.AES_IV)
        decrypted = unpad(cipher.decrypt(b64decode(enc_url)), AES.block_size)
        return decrypted.decode("utf-8")
    except Exception as e:
        return ""


def decrypt_txt_content(content: str) -> str:
    """
    Poore TXT content mein helper:// URLs dhundho aur decrypt karo.
    Normal URLs aur text as-is rehta hai.
    """
    lines = []
    for line in content.splitlines():
        match = re.search(r"(helper://\S+)", line)
        if match:
            enc_url   = match.group(1)
            dec_url   = decrypt_url(enc_url)
            if dec_url:
                line = line.replace(enc_url, dec_url)
        lines.append(line)
    return "\n".join(lines)
