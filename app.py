import os
import sqlite3
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, session
)
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cle-de-dev-a-changer")


def get_connexion():
    connexion = sqlite3.connect("stock.db")
    connexion.row_factory = sqlite3.Row
    return connexion


def connexion_requise(fonction):
    """Redirige vers /login si l'utilisateur n'est pas connecté."""
    @wraps(fonction)
    def enveloppe(*args, **kwargs):
        if "utilisateur" not in session:
            return redirect(url_for("login"))
        return fonction(*args, **kwargs)
    return enveloppe


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


@app.route("/login", methods=["GET", "POST"])
def login():
    erreur = None

    if request.method == "POST":
        nom = request.form["nom"].strip()
        mot_de_passe = request.form["mot_de_passe"]

        connexion = get_connexion()
        utilisateur = connexion.execute(
            "SELECT * FROM utilisateurs WHERE nom = ?", (nom,)
        ).fetchone()
        connexion.close()

        if utilisateur and check_password_hash(
            utilisateur["mot_de_passe_hash"], mot_de_passe
        ):
            session.clear()
            session["utilisateur"] = utilisateur["nom"]
            return redirect(url_for("accueil"))

        erreur = "Identifiants incorrects."

    return render_template("login.html", erreur=erreur)


@app.route("/deconnexion", methods=["POST"])
def deconnexion():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@connexion_requise
def accueil():
    connexion = get_connexion()
    produits = connexion.execute("SELECT * FROM produits").fetchall()
    connexion.close()
    return render_template("produits.html", produits=produits)


@app.route("/ajouter", methods=["GET", "POST"])
@connexion_requise
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
@connexion_requise
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
@connexion_requise
def supprimer(id):
    connexion = get_connexion()
    connexion.execute("DELETE FROM produits WHERE id = ?", (id,))
    connexion.commit()
    connexion.close()
    return redirect(url_for("accueil"))


@app.route("/vendre", methods=["GET", "POST"])
@connexion_requise
def vendre():
    connexion = get_connexion()
    erreur = None

    if request.method == "POST":
        try:
            produit_id = int(request.form["produit_id"])
            quantite = int(request.form["quantite"])
        except ValueError:
            produit_id, quantite = None, None
            erreur = "Données invalides."

        if erreur is None and quantite <= 0:
            erreur = "La quantité doit être supérieure à zéro."

        if erreur is None:
            resultat = connexion.execute(
                "UPDATE produits SET quantite = quantite - ? "
                "WHERE id = ? AND quantite >= ?",
                (quantite, produit_id, quantite),
            )
            if resultat.rowcount == 0:
                erreur = "Stock insuffisant ou produit introuvable."
            else:
                connexion.execute(
                    "INSERT INTO ventes (produit_id, quantite) VALUES (?, ?)",
                    (produit_id, quantite),
                )
                connexion.commit()
                connexion.close()
                return redirect(url_for("ventes"))

    produits = connexion.execute(
        "SELECT * FROM produits WHERE quantite > 0"
    ).fetchall()
    connexion.close()
    return render_template("vendre.html", produits=produits, erreur=erreur)


@app.route("/ventes")
@connexion_requise
def ventes():
    connexion = get_connexion()
    liste = connexion.execute(
        "SELECT ventes.id, produits.nom, ventes.quantite, produits.prix, "
        "ventes.quantite * produits.prix AS total, ventes.date_vente "
        "FROM ventes JOIN produits ON ventes.produit_id = produits.id "
        "ORDER BY ventes.id DESC"
    ).fetchall()
    connexion.close()
    return render_template("ventes.html", ventes=liste)


if __name__ == "__main__":
    app.run(debug=True)