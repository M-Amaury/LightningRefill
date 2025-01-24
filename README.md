# Lightning Gift Cards

Un système de cartes cadeaux utilisant le réseau Lightning en mode regtest. Ce projet permet de créer et gérer des cartes cadeaux via des paiements Lightning Network.

## Prérequis

- Linux/WSL
- Python 3.7+
- Bitcoin Core en mode regtest
- Core Lightning

## Installation

1. Clonez le repository
git clone https://github.com/M-Amaury/LightningRefill.git
cd LightningRefill

2. Créez un environnement virtuel Python
python3 -m venv venv
source venv/bin/activate

3. Installez les dépendances
pip install flask lightning-python qrcode pillow requests

4. Configurez les variables d'environnement
cp .env.example .env
# Éditez .env avec vos valeurs

## Configuration des nœuds Lightning

1. Lancez deux instances de Lightning en mode regtest
# Terminal 1 - Premier nœud (marchand)
lightningd --lightning-dir=/path/to/.lightning --network=regtest

# Terminal 2 - Second nœud (client)
lightningd --lightning-dir=/path/to/.lightning2 --network=regtest

2. Récupérez l'ID du premier nœud
lightning-cli --lightning-dir=/path/to/.lightning getinfo
# Notez l'ID du nœud dans la sortie

3. Connectez le second nœud au premier
lightning-cli --lightning-dir=/path/to/.lightning2 connect <NODE_ID_1>@<IP_ADDRESS>:<PORT>

4. Créez un canal entre les nœuds
# Depuis le premier nœud
lightning-cli --lightning-dir=/path/to/.lightning fundchannel <NODE_ID_2> <AMOUNT_IN_SATS>

## Configuration du projet

1. Modifiez le fichier .env avec les informations de vos nœuds :
# Nœud marchand (premier nœud)
LIGHTNING_RPC_PATH=/path/to/.lightning/regtest/lightning-rpc
MERCHANT_NODE_ID=<NODE_ID_1>

# Nœud client (second nœud)
CLIENT_RPC_PATH=/path/to/.lightning2/regtest/lightning-rpc
CLIENT_NODE_ID=<NODE_ID_2>

## Lancement du projet

1. Démarrez le serveur marchand
# Terminal 1
python3 lnurl_server.py

2. Démarrez le serveur client
# Terminal 2
python3 lnurl_client.py

3. Accédez à l'interface web
http://localhost:5001

## Utilisation

1. Sélectionnez une carte cadeau (25€, 50€ ou 100€)
2. Scannez le QR code ou copiez l'invoice Lightning
3. Effectuez le paiement
4. Récupérez votre code cadeau

## Notes importantes

- Ce projet est conçu pour fonctionner en mode regtest
- Assurez-vous d'avoir suffisamment de fonds dans vos canaux
- Les montants sont en satoshis (1 EUR ≈ 1000 sats dans cet exemple)
- Les chemins des fichiers RPC doivent avoir les bonnes permissions

## Dépannage

1. Vérifiez que les nœuds sont en cours d'exécution :
lightning-cli --lightning-dir=/path/to/.lightning getinfo
lightning-cli --lightning-dir=/path/to/.lightning2 getinfo

2. Vérifiez l'état des canaux :
lightning-cli --lightning-dir=/path/to/.lightning listchannels

3. Vérifiez les logs :
tail -f app.log
