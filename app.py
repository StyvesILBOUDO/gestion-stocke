import sqlite3
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)


def get_connexion():
    connexion = sqlite3.connect("stock.db")
    connexion.row_factory = sqlite3.Row
    return connexion


def valider_produit(nom, prix, quantite):
    """Retourne (prix, quantite, erreur)."""
    if not nom:
        return None, None, "Le nom du produit est obligatoire."
    try:
        prix = float(prix)
        quantite = int(quantite)
    except ValueError:
        return None, None, "Le prix et la quantité doivent être des nombres."
    if prix < 0 or quantite < 0:
        return None, None, "Le prix et la quantité ne peuvent pas être négatifs."
    return prix, quantite, None


@app.route("/")
def accueil():
    connexion = get_connexion()
    produits = connexion.execute("SELECT * FROM produits").fetchall()
    connexion.close()
    return render_template("produits.html", produits=produits)


@app.route("/ajouter", methods=["GET", "POST"])
def ajouter():
    erreur = None

    if request.method == "POST":
        nom = request.form["nom"].strip()
        prix, quantite, erreur = valider_produit(
            nom, request.form["prix"], request.form["quantite"]
        )

        if erreur is None:
            connexion = get_connexion()
            connexion.execute(
                "INSERT INTO produits (nom, prix, quantite) VALUES (?, ?, ?)",
                (nom, prix, quantite),
            )
            connexion.commit()
            connexion.close()
            return redirect(url_for("accueil"))

    return render_template("ajouter.html", erreur=erreur)


@app.route("/modifier/<int:id>", methods=["GET", "POST"])
def modifier(id):
    connexion = get_connexion()
    produit = connexion.execute(
        "SELECT * FROM produits WHERE id = ?", (id,)
    ).fetchone()

    if produit is None:
        connexion.close()
        return "Produit introuvable", 404

    erreur = None

    if request.method == "POST":
        nom = request.form["nom"].strip()
        prix, quantite, erreur = valider_produit(
            nom, request.form["prix"], request.form["quantite"]
        )

        if erreur is None:
            connexion.execute(
                "UPDATE produits SET nom = ?, prix = ?, quantite = ? WHERE id = ?",
                (nom, prix, quantite, id),
            )
            connexion.commit()
            connexion.close()
            return redirect(url_for("accueil"))

    connexion.close()
    return render_template("modifier.html", produit=produit, erreur=erreur)


@app.route("/supprimer/<int:id>", methods=["POST"])
def supprimer(id):
    connexion = get_connexion()
    connexion.execute("DELETE FROM produits WHERE id = ?", (id,))
    connexion.commit()
    connexion.close()
    return redirect(url_for("accueil"))


if __name__ == "__main__":
    app.run(debug=True)