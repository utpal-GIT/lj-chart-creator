"""
User Management CLI for LJ Chart Creator
Usage:
    python manage_users.py add <username> <password> [display_name] [--admin]
    python manage_users.py remove <username>
    python manage_users.py list
    python manage_users.py reset-password <username> <new_password>
"""

import sys
import json
import hashlib
import secrets
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
CREDENTIALS_FILE = DATA_DIR / "credentials.json"


def _hash_password(password: str, salt: str = None) -> tuple:
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return hashed, salt


def load_credentials() -> dict:
    if CREDENTIALS_FILE.exists():
        with open(CREDENTIALS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_credentials(creds: dict):
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(creds, f, indent=2)


def add_user(username: str, password: str, display_name: str = "", role: str = "user"):
    creds = load_credentials()
    if username in creds:
        print(f"User '{username}' already exists. Use 'reset-password' to change password.")
        return
    hashed, salt = _hash_password(password)
    creds[username] = {
        "hash": hashed,
        "salt": salt,
        "display_name": display_name or username,
        "role": role,
    }
    save_credentials(creds)
    print(f"User '{username}' created as {role}.")


def remove_user(username: str):
    creds = load_credentials()
    if username not in creds:
        print(f"User '{username}' not found.")
        return
    del creds[username]
    save_credentials(creds)
    print(f"User '{username}' removed. (Data files are preserved in data/{username}/)")


def list_users():
    creds = load_credentials()
    if not creds:
        print("No users found.")
        return
    print(f"{'Username':<20} {'Display Name':<25} {'Role':<10}")
    print("-" * 55)
    for uname, info in creds.items():
        dname = info.get("display_name", uname)
        role = info.get("role", "user")
        print(f"{uname:<20} {dname:<25} {role:<10}")
    print(f"\nTotal: {len(creds)} user(s)")


def reset_password(username: str, new_password: str):
    creds = load_credentials()
    if username not in creds:
        print(f"User '{username}' not found.")
        return
    hashed, salt = _hash_password(new_password)
    creds[username]["hash"] = hashed
    creds[username]["salt"] = salt
    save_credentials(creds)
    print(f"Password for '{username}' has been reset.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "add":
        if len(sys.argv) < 4:
            print("Usage: python manage_users.py add <username> <password> [display_name]")
            sys.exit(1)
        args = sys.argv[2:]
        uname = args[0].strip().lower()
        pwd = args[1]
        is_admin = "--admin" in args
        remaining = [a for a in args[2:] if a != "--admin"]
        dname = " ".join(remaining) if remaining else ""
        add_user(uname, pwd, dname, role="admin" if is_admin else "user")

    elif command == "remove":
        if len(sys.argv) < 3:
            print("Usage: python manage_users.py remove <username>")
            sys.exit(1)
        remove_user(sys.argv[2].strip().lower())

    elif command == "list":
        list_users()

    elif command == "reset-password":
        if len(sys.argv) < 4:
            print("Usage: python manage_users.py reset-password <username> <new_password>")
            sys.exit(1)
        reset_password(sys.argv[2].strip().lower(), sys.argv[3])

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)
