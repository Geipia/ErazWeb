import random
import hashlib
from consts import DIFFICULTY
import csv
import os
from backend.client import client
from internal.log import log_error

def generate_puzzle(eraz_id):
    """Génère un puzzle pour le minage."""
    return random.randint(1, 1000000)

def valid_solution(eraz_id, nonce):
    """Vérifie si la solution est valide pour le puzzle de minage."""
    hash_attempt = hashlib.sha256(f'{eraz_id}{nonce}'.encode()).hexdigest()
    return hash_attempt[:DIFFICULTY] == '0' * DIFFICULTY

def read_csv_file(csv_path: str):
    """Reads data from a remote CSV file."""
    data = []
    local_csv_path = "temp.csv"
    try:
        if client.check(csv_path):
            client.download_sync(remote_path=csv_path, local_path=local_csv_path)
            with open(local_csv_path, "r") as csv_file:
                reader = csv.reader(csv_file)
                data = [row for row in reader]
        else:
            log_error(f"CSV file not found at path: {csv_path}")
    except Exception as e:
        log_error(f"Failed to read data from CSV: {str(e)}")
    finally:
        if os.path.exists(local_csv_path):
            os.remove(local_csv_path)
    return data

def save_csv_file(csv_path: str, data: list):
    """Saves data to a remote CSV file."""
    local_csv_path = "temp.csv"
    try:
        with open(local_csv_path, "w", newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerows(data)
        client.upload_sync(remote_path=csv_path, local_path=local_csv_path)
    except Exception as e:
        log_error(f"Failed to save data to CSV: {str(e)}")
    finally:
        if os.path.exists(local_csv_path):
            os.remove(local_csv_path)

def create_remote_dirs(remote_path: str):
    """Ensures that all directories in the remote path exist."""
    parts = remote_path.strip("/").split("/")
    current_path = "/"
    for part in parts[:-1]:  # Exclude the file name
        current_path = os.path.join(current_path, part).replace("\\", "/")
        if not client.check(current_path):
            client.mkdir(current_path)