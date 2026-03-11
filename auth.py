"""
auth.py — Simple JSON based user auth
Channel forward se auto add hoga
"""
import json
import os
from config import Config

USERS_FILE = Config.USERS_FILE

def _load() -> list:
    if os.path.exists(USERS_FILE):
        try:
            return json.load(open(USERS_FILE))
        except Exception:
            return []
    return []

def _save(users: list):
    json.dump(users, open(USERS_FILE, "w"))

def is_owner(uid: int) -> bool:
    return uid == Config.OWNER_ID

def is_auth(uid: int) -> bool:
    if is_owner(uid):
        return True
    return uid in _load()

def add_user(uid: int):
    users = _load()
    if uid not in users:
        users.append(uid)
        _save(users)

def remove_user(uid: int):
    users = _load()
    if uid in users:
        users.remove(uid)
        _save(users)

def get_all_users() -> list:
    return _load()
