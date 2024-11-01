from flask import Flask, render_template, request, redirect, url_for, session, flash
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from backend.backend_db import *
from consts import *
from backend.backend_methods import *
import functools


app = Flask(__name__)
app.secret_key = 'ef88e21a-31bb-4448-b9a4-c2f6759c2778'
ERROR = False


def set_error(value: bool):
    global ERROR
    ERROR = value


@app.route('/')
def index():
    if ERROR:
        app.redirect('/error')
        return
    user_id = session.get('user_id')
    if user_id:
        wallets = wallet_manager.get_user_wallets(user_id)
        # Ne plus montere la blockchain dans index, que dans developerhome
        #return render_template('index.html', wallets=wallets.values(), blockchain=blockchain.chain)
        return render_template('index.html', wallets=wallets.values())
    else:
        return redirect(url_for('login'))


@app.route('/developerhome')
def developerhome():
    if ERROR:
        app.redirect('/error')
        return
    user_id = session.get('user_id')
    if user_id:
        wallets = wallet_manager.get_user_wallets(user_id)
        return render_template('developerhome.html', wallets=wallets.values(), blockchain=blockchain.chain)
    else:
        return redirect(url_for('developer'))


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


@app.route('/developer', methods=['GET', 'POST'])
def developer():
    if ERROR:
        app.redirect('/error')
        return
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        if user_manager.authenticate(user_id, password):
            session['user_id'] = user_id
            return redirect(url_for('developerhome'))
        else:
            flash('Invalid credentials. Please try again.')
    return redirect(url_for('/'))


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


# Caché: plus rapide si on essaye de miner plusieurs fois le même Eraz
@functools.lru_cache(maxsize=256)
def is_eraz_valid(eraz_id, nonce, wallet_id) -> bool:
    if eraz_id % 751953751953 == 0:
        if blockchain.eraz_id_exists(eraz_id):
            flash('Cet Eraz ID a déjà été miné.')
            return False
        elif blockchain.total_mined_eraz >= MAX_ERAZ:
            flash('Le maximum de 21 millions d\'Eraz a été atteint.')
            return False
        elif not valid_solution(eraz_id, nonce):
            flash(f'La solution est incorrecte. Essayez encore.')
            return False
        else:
            wallet = wallet_manager.get_wallet(wallet_id)
            if wallet:
                reward = blockchain.get_current_reward()
                # Vérifier que la récompense est positive
                if reward <= 0:
                    flash('Récompense invalide. Impossible de miner un nombre négatif ou nul d\'Eraz.')
                    return False
                else:
                    wallet.deposit(reward)
                    wallet_manager.save_wallets()
                    new_block = Block(eraz_id, blockchain.get_last_block().hash)
                    new_block.transactions.append(f"Eraz ID {eraz_id} miné par {wallet_id}, récompense: {reward}Eraz")
                    blockchain.add_block(new_block, reward)
                    update_eraz_value(reward)
                    return True
            else:
                flash('Portefeuille non trouvé.')
                return False
    else:
        flash('Eraz ID non valide. Doit être un multiple de 751953751953.')
        return False


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

        is_eraz_valid(eraz_id, nonce, wallet_id)
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
    """Affiche un graphique de la valeur de l'Eraz au fil du temps."""
    if ERROR:
        app.redirect('/error')
        return
    # Trop lent et inutile
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
    app.run(debug=False, port=5000)
