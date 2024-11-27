import os
import requests
from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_session import Session
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset


server = Server(horizon_url='https://horizon-testnet.stellar.org')

def create_app(test_config=None):
    
    app = Flask(__name__, instance_relative_config=True)
    app.secret_key = 'qqqq'  

    
    app.config['SESSION_TYPE'] = 'filesystem'
    Session(app)

    # Home page
    @app.route('/')
    def index():
        return render_template('index.html')

    
    @app.route('/account', methods=('GET', 'POST'))
    def account():
        
        if 'pubkey' in request.form:
            pub_key = request.form['pubkey']
            session['pub_key'] = pub_key
        else:
            pub_key = session.get('pub_key', None)

        if pub_key is None:
            flash('Public key not found in session.')
            return redirect(url_for('index'))

        
        try:
            r = requests.get(accounts_url.format(pub_key))
            r.raise_for_status()
            json_obj = r.json()
        except requests.RequestException as e:
            flash(f'Error fetching account details: {e}')
            return redirect(url_for('index'))

        
        session['balances'] = json_obj
        return render_template('account.html', pub_key=pub_key, json_obj=json_obj)

    
    @app.route('/store_private_key', methods=('POST',))
    def store_private_key():
        private_key = request.form['private_key']
        session['private_key'] = private_key
        flash('Private key stored successfully.')
        return redirect(url_for('account'))

    
    @app.route('/send_xlm', methods=('POST',))
    def send_xlm():
        recipient = request.form['recipient']
        amount = request.form['amount']

        if 'pub_key' not in session:
            flash('No public key found in session.')
            return redirect(url_for('index'))

        pub_key = session['pub_key']
        private_key = session.get('private_key')

        if private_key is None:
            flash('Private key is required to sign the transaction.')
            return redirect(url_for('account'))

        try:
            source_keypair = Keypair.from_secret(private_key)
            source_account = server.load_account(account_id=source_keypair.public_key)

            transaction = TransactionBuilder(
                source_account=source_account,
                network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
                base_fee=100 
            ).add_text_memo("Test Transaction").append_payment_op(
                destination=recipient,
                amount=amount,
                asset=Asset.native()
            ).set_timeout(30).build()

            transaction.sign(source_keypair)
            response = server.submit_transaction(transaction)

            flash(f'Transaction successful! ID: {response["hash"]}')
            flash(f'Amount sent: {amount} XLM')

           
            r = requests.get(accounts_url.format(pub_key))
            r.raise_for_status()
            json_obj = r.json()
            session['balances'] = json_obj

            
            old_balance = float(session['balances']['balances'][0]['balance'])
            new_balance = float(json_obj['balances'][0]['balance'])
            debug_info = {
                'Old Balance': old_balance,
                'Amount Sent': amount,
                'New Balance': new_balance,
                'Balance Difference': old_balance - new_balance
            }
            print(debug_info)
            flash(f'Debug Info: {debug_info}')

        except Exception as e:
            flash(f'Transaction failed: {e}')

        return redirect(url_for('account'))

    return app
