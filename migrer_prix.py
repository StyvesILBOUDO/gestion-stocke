import sqlite3

connexion = sqlite3.connect("stock.db")

colonnes = [c[1] for c in connexion.execute("PRAGMA table_info(ventes)")]
if "prix_unitaire" not in colonnes:
    connexion.execute("ALTER TABLE ventes ADD COLUMN prix_unitaire REAL")

connexion.execute(
    "UPDATE ventes SET prix_unitaire = "
    "(SELECT prix FROM produits WHERE produits.id = ventes.produit_id) "
    "WHERE prix_unitaire IS NULL"
)
connexion.commit()
connexion.close()
print("Base mise à jour.")