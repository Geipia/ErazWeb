from flask import Flask, render_template, request, redirect, url_for, session, flash
import uuid
import os
import csv
import hashlib
import random
import datetime
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Changez cette clé secrète pour sécuriser les sessions

# Constants
MAX_ERAZ = 21000000  # 21 million Eraz limit
INITIAL_REWARD = 1  # Initial reward for mining
REWARD_HALVING_INTERVAL = 4  # Reward halves every 4 years
DIFFICULTY = 7  # Number of leading zeros required in the hash
VALUE_FILE = 'eraz_values.csv'  # Fichier pour stocker les valeurs d'Eraz

# Valeur initiale de l'Eraz en euros
initial_eraz_value = 0.25  # 1 euro

ERROR = False

if not os.path.exists(VALUE_FILE):
    with open(VALUE_FILE, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['timestamp', 'value'])
        writer.writerow([datetime.datetime.now().isoformat(), initial_eraz_value])


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


def generate_puzzle(eraz_id):
    """Génère un puzzle pour le minage."""
    return random.randint(1, 1000000)


def valid_solution(eraz_id, nonce):
    """Vérifie si la solution est valide pour le puzzle de minage."""
    hash_attempt = hashlib.sha256(f'{eraz_id}{nonce}'.encode()).hexdigest()
    return hash_attempt[:DIFFICULTY] == '0' * DIFFICULTY


def update_eraz_value(minedamount: float = 0):
    """Met à jour la valeur de l'Eraz pour tout le monde."""
    with open(VALUE_FILE, 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header
        last_row = list(reader)[-1]  # Get last row
        last_value = float(last_row[1])

    # Simule une légère augmentation ou diminution de la valeur
    new_value = last_value - minedamount / 10000 if minedamount / 10000 < last_value else 0
    if new_value <= 0:
        app.redirect('/error')
        ERROR = True
        print('FATAL ERROR: Eraz value can never be negative.')
        #RuntimeError("Eraz value can never be negative")

    with open(VALUE_FILE, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([datetime.datetime.now().isoformat(), new_value])


def get_eraz_values():
    """Récupère les valeurs de l'Eraz depuis le fichier CSV."""
    with open(VALUE_FILE, 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header
        return [(datetime.datetime.fromisoformat(row[0]), float(row[1])) for row in reader]


@app.route('/')
def index():
    if ERROR:
        app.redirect('/error')
        return
    user_id = session.get('user_id')
    if user_id:
        wallets = wallet_manager.get_user_wallets(user_id)
        return render_template('index.html', wallets=wallets.values(), blockchain=blockchain.chain)
    else:
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if ERROR:
        app.redirect('/error')
        return
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        if user_manager.authenticate(user_id, password):
            session['user_id'] = user_id
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials. Please try again.')
    return render_template('login.html')


@app.route('/logout')
def logout():
    if ERROR:
        app.redirect('/error')
        return
    session.pop('user_id', None)
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if ERROR:
        app.redirect('/error')
        return
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        if user_manager.user_exists(user_id):
            flash('User ID already exists. Please choose another one.')
        else:
            user_manager.add_user(user_id, password)
            wallet_manager.create_wallet(user_id)
            flash('Registration successful. You can now log in.')
            return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/create_wallet', methods=['POST'])
def create_wallet():
    if ERROR:
        app.redirect('/error')
        return
    user_id = session.get('user_id')
    if user_id:
        wallet_manager.create_wallet(user_id)
        return redirect(url_for('index'))
    else:
        return redirect(url_for('login'))


@app.route('/mine', methods=['POST'])
def mine():
    if ERROR:
        app.redirect('/error')
        return
    user_id = session.get('user_id')
    if user_id:
        wallet_id = request.form['wallet_id']
        eraz_id = int(request.form['eraz_id'])
        nonce = int(request.form['nonce'])

        if eraz_id % 751953751953 == 0:
            if blockchain.eraz_id_exists(eraz_id):
                flash('Cet Eraz ID a déjà été miné.')
            elif blockchain.total_mined_eraz >= MAX_ERAZ:
                flash('Le maximum de 21 millions d\'Eraz a été atteint.')
            elif not valid_solution(eraz_id, nonce):
                flash(f'La solution est incorrecte. Essayez encore.')
            else:
                wallet = wallet_manager.get_wallet(wallet_id)
                if wallet:
                    reward = blockchain.get_current_reward()

                    # Vérifier que la récompense est positive
                    if reward <= 0:
                        flash('Récompense invalide. Impossible de miner un nombre négatif ou nul d\'Eraz.')
                    else:
                        wallet.deposit(reward)
                        wallet_manager.save_wallets()

                        new_block = Block(eraz_id, blockchain.get_last_block().hash)
                        new_block.transactions.append(f"Eraz ID {eraz_id} miné par {wallet_id}, récompense: {reward} Eraz")
                        blockchain.add_block(new_block, reward)

                        update_eraz_value(reward)

                        return redirect(url_for('index'))
                else:
                    flash('Portefeuille non trouvé.')
        else:
            flash('Eraz ID non valide. Doit être un multiple de 751953751953.')
    return redirect(url_for('index'))


@app.route('/transaction', methods=['POST'])
def transaction():
    if ERROR:
        app.redirect('/')
        return
    user_id = session.get('user_id')
    if user_id:
        sender_wallet_id = request.form['sender_wallet_id']
        recipient_wallet_id = request.form['recipient_wallet_id']
        amount = float(request.form['amount'])

        if amount <= 0:
            flash('Le montant de la transaction doit être positif.')
            return redirect(url_for('index'))

        sender_wallet = wallet_manager.get_wallet(sender_wallet_id)
        recipient_wallet = wallet_manager.get_wallet(recipient_wallet_id)

        if sender_wallet and recipient_wallet:
            if sender_wallet.withdraw(amount):
                recipient_wallet.deposit(amount)
                wallet_manager.save_wallets()
                blockchain.add_transaction(sender_wallet_id, recipient_wallet_id, amount)
                flash(f'Transaction de {amount} Eraz effectuée de {sender_wallet_id} à {recipient_wallet_id}.')
                return redirect(url_for('index'))
            else:
                flash('Solde insuffisant.')
        else:
            flash('Portefeuille introuvable.')
    return redirect(url_for('index'))


@app.route('/get_difficulty', methods=['GET'])
def get_difficulty():
    return {'difficulty': DIFFICULTY}, 200



@app.route('/graph')
def graph():
    if ERROR:
        app.redirect('/error')
        return
    """Affiche un graphique de la valeur de l'Eraz au fil du temps."""
    #update_eraz_value()  # Mettez à jour la valeur avant de tracer le graphique
    eraz_values = get_eraz_values()
    dates = [point[0] for point in eraz_values]
    values = [point[1] for point in eraz_values]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, values, marker='o')
    plt.title("Oscillation de la valeur de l'Eraz (€)")
    plt.xlabel("Temps")
    plt.ylabel("Oscillation de la valeur (€)")
    plt.grid(True)

    # Convertir le graphique en image pour affichage dans une page HTML
    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    graph_url = base64.b64encode(img.getvalue()).decode('utf8')

    return render_template('graph.html', graph_url=graph_url)



@app.route('/error')
def fatal_error():
    return render_template('error.html')


if __name__ == '__main__':
    user_manager = UserManager()
    wallet_manager = WalletManager()
    blockchain = Blockchain()
    blockchain.load_chain()
    app.run(debug=True, port = 5000)
