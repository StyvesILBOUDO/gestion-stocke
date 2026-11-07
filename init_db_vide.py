import sqlite3

connexion = sqlite3.connect("stock.db")

with open("schema.sql", encoding="utf-8") as fichier:
    connexion.executescript(fichier.read())

connexion.commit()
connexion.close()
print("Base de données vide créée avec succès.")