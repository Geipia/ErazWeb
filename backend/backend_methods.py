import random
import hashlib
from consts import DIFFICULTY

def generate_puzzle(eraz_id):
    """Génère un puzzle pour le minage."""
    return random.randint(1, 1000000)


def valid_solution(eraz_id, nonce):
    """Vérifie si la solution est valide pour le puzzle de minage."""
    hash_attempt = hashlib.sha256(f'{eraz_id}{nonce}'.encode()).hexdigest()
    return hash_attempt[:DIFFICULTY] == '0' * DIFFICULTY
