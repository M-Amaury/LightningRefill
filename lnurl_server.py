from flask import Flask, jsonify, request
from pyln.client import LightningRpc
from hashlib import sha256
import logging
import os
from datetime import datetime
import uuid
import json
import secrets
import sqlite3
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('app.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Core Lightning node configuration
LIGHTNING_RPC_PATH = os.getenv('LIGHTNING_RPC_PATH')
METADATA_PLAIN = "Payment for services"
METADATA = f"""[["text/plain","{METADATA_PLAIN}"]]"""

MERCHANT_NODE_ID = os.getenv('MERCHANT_NODE_ID')

def get_client():
    logger.info("Getting an instance of the LightningRpc client...")
    """Get an instance of the LightningRpc client."""
    try:
        return LightningRpc(LIGHTNING_RPC_PATH)
    except Exception as e:
        logger.error(f"Error connecting to LightningRpc: {e}")
        raise

def get_node_connect_info():
    logger.info("Getting the node's connection info...")
    """Get the node's connection info."""
    node = get_client()
    node_info = node.getinfo()
    first_address = node_info['address'][0]
    return f"{node_info['id']}@{first_address['address']}:{first_address['port']}"

def get_random_id():
    logger.info("Generating a random k1 identifier...")
    """Generate a random k1 identifier."""
    return os.urandom(12).hex()

def get_callback(tag):
    logger.info("Generating callback URLs...")
    """Generate callback URLs."""
    if tag == "channelRequest":
        return f"lnurl-channel-request"
    elif tag == "payRequest":
        return f"lnurl-pay"

def generate_invoice(amount):
    logger.info(f"Generating an invoice for {amount} millisatoshis...")
    """Generate a real invoice from the Core Lightning node."""
    node = get_client()
    try:
        # Create a unique label for the invoice
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        unique_id = uuid.uuid4().hex[:8]  # Short unique ID
        label = f"invoice_{timestamp}_{unique_id}"
        invoice = node.invoice(amount, f"{label}", f"{sha256(METADATA.encode("utf-8")).hexdigest()}")
        logger.info(f"Generated invoice: {invoice}")
        return invoice
    except Exception as e:
        logger.error(f"Error generating invoice: {e}")
        return None

@app.route("/lnurl-channel-request", methods=["GET"])
def answer_channel_request():
    logger.info("Handling channel requests...")
    """Handle channel requests."""
    k1 = request.args.get("k1")
    remote_id = request.args.get("remote_id")
    announce = False if request.args.get("private")==1 else True
    amount = int(request.args.get("amount"))
    try:
        client = get_client()
        res = client.fundchannel(node_id=remote_id, amount=amount, announce=announce) 
        return jsonify({"status": "OK", "result": res})
    except Exception as e:
        return jsonify({"status": "ERROR", "reason": str(e)}), 500

@app.route("/lnurl2", methods=["GET"])
def lnurl_channel():
    logger.info("Handling LNURL2 requests...")
    """LNURL-channel endpoint to open channel to client."""
    try:
        tag = "channelRequest"
        node_info = get_node_connect_info()
        logger.info(f"Node info: {node_info}")
        k1 = get_random_id()
        logger.info(f"Generated k1: {k1}")
        callback = get_callback(tag)
        logger.info(f"Callback URL: {callback}")
        return jsonify({
            "status": "OK",
            "tag": tag,
            "uri": node_info,
            "k1": k1,
            "callback": callback,
        })
    except Exception as e:
        logger.error(f"Error in lnurl2: {e}")
        return jsonify({"status": "ERROR", "reason": str(e)}), 500

@app.route("/lnurl-pay", methods=["GET"])
def lnurl_answer_pay():
    logger.info("Handling LNURL-pay requests...")
    """LNURL-pay endpoint to generate invoices."""
    try:
        amount = int(request.args.get("amount"))  # Amount in millisatoshis
        invoice = generate_invoice(amount)
        bolt11 = invoice['bolt11']
        # logger.info(f"Generated invoice: {invoice}")
        return jsonify({
            "pr": f"{bolt11}",
            "routes": [],
        })
    except Exception as e:
        logger.error(f"Error in lnurl-pay: {e}")
        return jsonify({"status": "ERROR", "reason": f"{e}"}), 500
    
@app.route("/lnurl6", methods=["GET"])
def lnurl_pay():
    logger.info("Handling LNURL3 requests...")
    """LNURL3 endpoint to pay invoices."""
    try:
        tag = "payRequest"
        callback = get_callback(tag)
        max_sendable = 1_000_000
        min_sendable = 1_000
        return jsonify({
            "callback": callback,
            "maxSendable": max_sendable,
            "minSendable": min_sendable,
            "metadata": METADATA,
            "tag": tag,
        })
    except Exception as e:
        return jsonify({"status": "ERROR", "reason": str(e)}), 500
    
@app.route("/.well-known/lnurlp/sosthene", methods=["GET"])
def lnurlp():
    logger.info("Handling LNURLp requests...")
    """LNURLp endpoint to pay invoices."""
    try:
        with open("/home/aespieux/.well-known/lnurlp/sosthene", "r") as f:
            return jsonify(f.read()), 200
    except Exception as e:
        return jsonify({"status": "ERROR", "reason": str(e)}), 500

# Base de données pour les cartes cadeaux
def init_db():
    conn = sqlite3.connect('gift_cards.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS gift_cards
        (id TEXT PRIMARY KEY, 
         amount INTEGER,
         payment_hash TEXT,
         code TEXT,
         status TEXT,
         created_at TIMESTAMP)
    ''')
    conn.commit()
    conn.close()

# Prix en satoshis (1 EUR ≈ 1000 sats pour l'exemple)
PRICES = {
    "25": 25000,  # 25 EUR
    "50": 50000,  # 50 EUR
    "100": 100000 # 100 EUR
}

@app.route('/api/create_invoice/<amount>', methods=['GET'])
def create_invoice(amount):
    print(f"Tentative de création d'une facture pour {amount}€")  # Log
    
    if amount not in PRICES:
        print(f"Montant invalide: {amount}")  # Log
        return jsonify({"error": "Montant invalide"}), 400
    
    sats_amount = PRICES[amount]
    label = f"giftcard_{secrets.token_hex(8)}"
    
    try:
        # Vérifier que nous utilisons le bon nœud
        client = get_client()
        print("Client Lightning connecté")  # Log
        
        node_info = client.getinfo()
        print(f"ID du nœud: {node_info['id']}")  # Log
        
        if node_info['id'] != MERCHANT_NODE_ID:
            print(f"Mauvais nœud: attendu {MERCHANT_NODE_ID}, reçu {node_info['id']}")  # Log
            return jsonify({"error": "Configuration incorrecte du nœud"}), 500

        # Vérifier que le nœud a des canaux actifs
        channels = client.listchannels()['channels']
        active_channels = [c for c in channels if c['active'] and c['source'] == MERCHANT_NODE_ID]
        print(f"Nombre de canaux actifs: {len(active_channels)}")  # Log
        
        if not active_channels:
            print("Aucun canal actif trouvé")  # Log
            return jsonify({"error": "Aucun canal actif disponible"}), 500

        # Créer la facture
        print(f"Création de la facture pour {sats_amount} sats")  # Log
        invoice = client.invoice(
            amount_msat=sats_amount * 1000,
            label=label,
            description=f"Carte cadeau {amount}€"
        )
        
        print(f"Facture créée: {invoice['bolt11']}")  # Log
        
        # Sauvegarder dans la base de données
        conn = sqlite3.connect('gift_cards.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO gift_cards (id, amount, payment_hash, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (label, amount, invoice['payment_hash'], 'pending', datetime.now()))
        conn.commit()
        conn.close()
        print("Facture sauvegardée dans la base de données")  # Log
        
        return jsonify({
            "payment_request": invoice['bolt11'],
            "payment_hash": invoice['payment_hash']
        })
    except Exception as e:
        print(f"Erreur détaillée lors de la création de la facture: {str(e)}")  # Log détaillé
        print(f"Type d'erreur: {type(e)}")  # Log du type d'erreur
        import traceback
        print(f"Traceback: {traceback.format_exc()}")  # Log du traceback complet
        return jsonify({"error": f"Erreur lors de la création de la facture: {str(e)}"}), 500

@app.route('/api/check_payment/<payment_hash>', methods=['GET'])
def check_payment(payment_hash):
    try:
        # Vérifier le statut du paiement
        invoices = get_client().listinvoices()['invoices']
        for inv in invoices:
            if inv['payment_hash'] == payment_hash:
                if inv['status'] == 'paid':
                    # Générer code carte cadeau
                    gift_code = f"GIFT-{secrets.token_hex(8)}"
                    
                    # Mettre à jour la base de données
                    conn = sqlite3.connect('gift_cards.db')
                    c = conn.cursor()
                    c.execute('''
                        UPDATE gift_cards 
                        SET status = ?, code = ?
                        WHERE payment_hash = ?
                    ''', ('completed', gift_code, payment_hash))
                    conn.commit()
                    conn.close()
                    
                    return jsonify({
                        "paid": True,
                        "gift_code": gift_code
                    })
                return jsonify({"paid": False})
        return jsonify({"paid": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/test_node', methods=['GET'])
def test_node():
    try:
        client = get_client()
        node_info = client.getinfo()
        channels = client.listchannels()['channels']
        active_channels = [c for c in channels if c['active'] and c['source'] == MERCHANT_NODE_ID]
        
        return jsonify({
            "node_id": node_info['id'],
            "is_merchant_node": node_info['id'] == MERCHANT_NODE_ID,
            "active_channels": len(active_channels),
            "total_channels": len(channels)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    logger.info("Starting LNURL server...")
    init_db()
    app.run(host="0.0.0.0", port=5000)  # Run locally on port 5000