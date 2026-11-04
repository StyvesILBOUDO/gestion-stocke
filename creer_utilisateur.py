import sqlite3
from getpass import getpass
from werkzeug.security import generate_password_hash

nom = input("Nom d'utilisateur : ").strip()
mot_de_passe = getpass("Mot de passe (min. 8 caractères) : ")

if not nom or len(mot_de_passe) < 8:
    print("Nom vide ou mot de passe trop court.")
    raise SystemExit(1)

connexion = sqlite3.connect("stock.db")
connexion.execute(
    """
    CREATE TABLE IF NOT EXISTS utilisateurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL UNIQUE,
        mot_de_passe_hash TEXT NOT NULL
    )
    """
)

try:
    connexion.execute(
        "INSERT INTO utilisateurs (nom, mot_de_passe_hash) VALUES (?, ?)",
        (nom, generate_password_hash(mot_de_passe)),
    )
    connexion.commit()
    print("Utilisateur créé avec succès.")
except sqlite3.IntegrityError:
    print("Ce nom d'utilisateur existe déjà.")
finally:
    connexion.close()