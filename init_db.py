import sqlite3

connexion = sqlite3.connect("stock.db")

with open("schema.sql", encoding="utf-8") as fichier:
    connexion.executescript(fichier.read())

connexion.execute(
    "INSERT INTO produits (nom, prix, quantite) VALUES (?, ?, ?)",
    ("Savon", 500, 50),
)
connexion.execute(
    "INSERT INTO produits (nom, prix, quantite) VALUES (?, ?, ?)",
    ("Sucre 1kg", 900, 30),
)

connexion.commit()
connexion.close()
print("Base de données créée avec succès.")