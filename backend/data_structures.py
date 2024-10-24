from werkzeug.security import generate_password_hash, check_password_hash
import csv
import os
import uuid
from consts import *
from backend.backend_methods import *

class User:
    def __init__(self, user_id, password_hash):
        self.user_id = user_id
        self.password_hash = password_hash

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'password_hash': self.password_hash
        }

    @staticmethod
    def from_dict(data):
        return User(data['user_id'], data['password_hash'])


class UserManager:
    def __init__(self, filepath='users.csv'):
        self.filepath = filepath
        self.users = self.load_users()

    def add_user(self, user_id, password):
        password_hash = generate_password_hash(password)
        user = User(user_id, password_hash)
        self.users[user_id] = user
        self.save_users()

    def authenticate(self, user_id, password):
        user = self.users.get(user_id)
        if user and check_password_hash(user.password_hash, password):
            return True
        return False

    def user_exists(self, user_id):
        return user_id in self.users

    def save_users(self):
        with open(self.filepath, 'w', newline='') as csvfile:
            fieldnames = ['user_id', 'password_hash']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for user in self.users.values():
                writer.writerow(user.to_dict())

    def load_users(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                return {row['user_id']: User.from_dict(row) for row in reader}
        return {}


class Wallet:
    def __init__(self, wallet_id=None):
        self.wallet_id = wallet_id or str(uuid.uuid4())
        self.balance = 0

    def deposit(self, amount):
        self.balance += amount

    def withdraw(self, amount):
        if self.balance >= amount:
            self.balance -= amount
            return True
        return False

    def to_dict(self):
        return {
            'wallet_id': self.wallet_id,
            'balance': self.balance
        }

    @staticmethod
    def from_dict(data):
        wallet = Wallet(data['wallet_id'])
        wallet.balance = float(data['balance'])
        return wallet

    def __str__(self):
        return f"Wallet ID: {self.wallet_id} | Balance: {self.balance}"


class WalletManager:
    def __init__(self, filepath='wallets.csv'):
        self.filepath = filepath
        self.wallets = self.load_wallets()

    def create_wallet(self, user_id):
        from backend.backend_db import update_eraz_value
        wallet = Wallet(wallet_id=f"{user_id}-{uuid.uuid4()}")
        self.wallets[wallet.wallet_id] = wallet
        self.save_wallets()
        update_eraz_value(-5)
        return wallet

    def get_wallet(self, wallet_id):
        return self.wallets.get(wallet_id)

    def get_user_wallets(self, user_id):
        return {wid: wallet for wid, wallet in self.wallets.items() if wallet.wallet_id.startswith(user_id)}

    def save_wallets(self):
        with open(self.filepath, 'w', newline='') as csvfile:
            fieldnames = ['wallet_id', 'balance']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for wallet in self.wallets.values():
                writer.writerow(wallet.to_dict())

    def load_wallets(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                return {row['wallet_id']: Wallet.from_dict(row) for row in reader}
        return {}


class Block:
    def __init__(self, eraz_id, previous_hash, transactions=None):
        self.eraz_id = eraz_id
        self.previous_hash = previous_hash
        self.transactions = transactions if transactions is not None else []
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        sha = hashlib.sha256()
        sha.update(f'{self.eraz_id}'.encode())
        return sha.hexdigest()

    def add_transaction(self, transaction):
        self.transactions.append(transaction)

    def to_dict(self):
        return {
            'eraz_id': self.eraz_id,
            'previous_hash': self.previous_hash,
            'hash': self.hash,
            'transactions': self.transactions
        }

    @staticmethod
    def from_dict(data):
        block = Block(data['eraz_id'], data['previous_hash'], data['transactions'])
        block.hash = data['hash']
        return block

    def __str__(self):
        return f"ID: {self.eraz_id}, Hash: {self.hash}, Previous Hash: {self.previous_hash}, Transactions: {self.transactions}"


class Blockchain:
    def __init__(self, filepath='blockchain.csv', mined_ids_filepath='mined_eraz_ids.csv'):
        self.chain = []
        self.total_mined_eraz = 0
        self.filepath = filepath
        self.mined_ids_filepath = mined_ids_filepath
        self.mined_eraz_ids = self.load_mined_eraz_ids()
        self.load_chain()

    def save_mined_eraz_id(self, eraz_id):
        """Saves a mined Eraz ID to the persistent storage."""
        with open(self.mined_ids_filepath, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([eraz_id])
        self.mined_eraz_ids.add(eraz_id)

    def load_mined_eraz_ids(self):
        """Loads mined Eraz IDs from the persistent storage."""
        if os.path.exists(self.mined_ids_filepath):
            with open(self.mined_ids_filepath, 'r') as csvfile:
                reader = csv.reader(csvfile)
                return {int(row[0]) for row in reader}
        return set()

    def eraz_id_exists(self, eraz_id):
        """Check if an Eraz ID has already been mined."""
        return eraz_id in self.mined_eraz_ids

    def add_block(self, new_block, reward):
        new_block.previous_hash = self.get_last_block().hash
        new_block.hash = new_block.calculate_hash()
        self.chain.append(new_block)
        self.total_mined_eraz += reward
        self.save_mined_eraz_id(new_block.eraz_id)
        self.save_chain()

    def create_genesis_block(self):
        return Block(0, "0")

    def get_last_block(self):
        return self.chain[-1]

    def save_chain(self):
        with open(self.filepath, 'w', newline='') as csvfile:
            fieldnames = ['eraz_id', 'previous_hash', 'hash', 'transactions']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for block in self.chain:
                writer.writerow(block.to_dict())

    def load_chain(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                self.chain = [Block.from_dict(row) for row in reader]
                self.total_mined_eraz = sum([INITIAL_REWARD / (2 ** (i // REWARD_HALVING_INTERVAL))
                                             for i in range(len(self.chain))])
        else:
            self.chain = [self.create_genesis_block()]

    def get_current_reward(self):
        """Retourne la récompense actuelle, en tenant compte des réductions."""
        halving_count = len(self.chain) // (REWARD_HALVING_INTERVAL * 365 * 24 * 6)  # assuming 1 block every 10 minutes
        return max(INITIAL_REWARD / (2 ** halving_count), 0)

    def add_transaction(self, sender_wallet_id, recipient_wallet_id, amount):
        """Ajoute une transaction à la blockchain."""
        new_block = Block(len(self.chain), self.get_last_block().hash)
        new_block.add_transaction(f"{sender_wallet_id} envoie {amount} Eraz à {recipient_wallet_id}")
        self.chain.append(new_block)
        self.save_chain()
