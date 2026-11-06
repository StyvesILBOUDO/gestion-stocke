import csv
import io
import os
import sqlite3
from datetime import date, timedelta
from functools import wraps

from flask import (
    Flask, Response, render_template, request, redirect, url_for, session
)
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cle-de-dev-a-changer")

SEUIL_STOCK = 10
TRIS = {"nom": "nom", "prix": "prix", "stock": "quantite"}
MOIS = [
    "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
    "août", "septembre", "octobre", "novembre", "décembre",
]


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


def calculer_periode(periode, ref):
    """Retourne (debut, fin, precedent, suivant, libelle). 'fin' est exclue."""
    if periode == "jour":
        debut = ref
        fin = ref + timedelta(days=1)
        precedent = ref - timedelta(days=1)
        suivant = fin
        libelle = f"Le {ref:%d/%m/%Y}"
    elif periode == "semaine":
        debut = ref - timedelta(days=ref.weekday())
        fin = debut + timedelta(days=7)
        precedent = debut - timedelta(days=7)
        suivant = fin
        dernier = fin - timedelta(days=1)
        libelle = f"Du {debut:%d/%m/%Y} au {dernier:%d/%m/%Y}"
    else:
        debut = ref.replace(day=1)
        if debut.month == 12:
            fin = date(debut.year + 1, 1, 1)
        else:
            fin = date(debut.year, debut.month + 1, 1)
        precedent = (debut - timedelta(days=1)).replace(day=1)
        suivant = fin
        libelle = f"{MOIS[debut.month - 1].capitalize()} {debut.year}"
    return debut, fin, precedent, suivant, libelle


def lire_periode():
    """Lit la période et la date de référence dans l'adresse."""
    periode = request.args.get("periode", "jour")
    if periode not in ("jour", "semaine", "mois"):
        periode = "jour"
    try:
        ref = date.fromisoformat(request.args.get("date", ""))
    except ValueError:
        ref = date.today()
    return periode, ref


def donnees_rapport(periode, ref):
    """Calcule les ventes regroupées par produit pour la période."""
    debut, fin, precedent, suivant, libelle = calculer_periode(periode, ref)
    bornes = (debut.isoformat(), fin.isoformat())

    connexion = get_connexion()
    lignes = connexion.execute(
        "SELECT produits.nom, SUM(ventes.quantite) AS quantite, "
        "SUM(ventes.quantite * ventes.prix_unitaire) AS total "
        "FROM ventes JOIN produits ON ventes.produit_id = produits.id "
        "WHERE date(ventes.date_vente) >= ? AND date(ventes.date_vente) < ? "
        "GROUP BY produits.id ORDER BY total DESC",
        bornes,
    ).fetchall()
    nb_ventes = connexion.execute(
        "SELECT COUNT(*) AS n FROM ventes "
        "WHERE date(date_vente) >= ? AND date(date_vente) < ?",
        bornes,
    ).fetchone()["n"]
    connexion.close()

    return lignes, nb_ventes, debut, precedent, suivant, libelle


def securiser_csv(texte):
    """Évite qu'Excel interprète un texte comme une formule."""
    if texte and texte[0] in "=+-@":
        return "'" + texte
    return texte


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
    q = request.args.get("q", "").strip()
    tri = request.args.get("tri", "nom")
    ordre = request.args.get("ordre", "asc")

    # Liste blanche : on n'accepte que des valeurs connues pour le tri
    if tri not in TRIS:
        tri = "nom"
    if ordre not in ("asc", "desc"):
        ordre = "asc"
    colonne = TRIS[tri]
    sens = "ASC" if ordre == "asc" else "DESC"

    connexion = get_connexion()
    produits = connexion.execute(
        f"SELECT * FROM produits WHERE nom LIKE ? ORDER BY {colonne} {sens}, id ASC",
        (f"%{q}%",),
    ).fetchall()
    alertes = connexion.execute(
        "SELECT nom, quantite FROM produits WHERE quantite < ? "
        "ORDER BY quantite ASC, nom ASC",
        (SEUIL_STOCK,),
    ).fetchall()
    nb_total = connexion.execute(
        "SELECT COUNT(*) AS n FROM produits"
    ).fetchone()["n"]
    connexion.close()

    return render_template(
        "produits.html",
        produits=produits,
        alertes=alertes,
        nb_total=nb_total,
        seuil=SEUIL_STOCK,
        q=q,
        tri=tri,
        ordre=ordre,
    )


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
                prix = connexion.execute(
                    "SELECT prix FROM produits WHERE id = ?", (produit_id,)
                ).fetchone()["prix"]
                connexion.execute(
                    "INSERT INTO ventes (produit_id, quantite, prix_unitaire) "
                    "VALUES (?, ?, ?)",
                    (produit_id, quantite, prix),
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
        "SELECT ventes.id, produits.nom, ventes.quantite, "
        "ventes.prix_unitaire AS prix, "
        "ventes.quantite * ventes.prix_unitaire AS total, ventes.date_vente "
        "FROM ventes JOIN produits ON ventes.produit_id = produits.id "
        "ORDER BY ventes.id DESC"
    ).fetchall()
    connexion.close()
    return render_template("ventes.html", ventes=liste)


@app.route("/rapport")
@connexion_requise
def rapport():
    periode, ref = lire_periode()
    lignes, nb_ventes, debut, precedent, suivant, libelle = donnees_rapport(
        periode, ref
    )

    return render_template(
        "rapport.html",
        lignes=lignes,
        periode=periode,
        libelle=libelle,
        ref=ref.isoformat(),
        precedent=precedent.isoformat(),
        suivant=suivant.isoformat(),
        aujourdhui=date.today().isoformat(),
        nb_ventes=nb_ventes,
        total_montant=sum(l["total"] for l in lignes),
        total_quantite=sum(l["quantite"] for l in lignes),
    )


@app.route("/rapport/export")
@connexion_requise
def rapport_export():
    periode, ref = lire_periode()
    lignes, nb_ventes, debut, precedent, suivant, libelle = donnees_rapport(
        periode, ref
    )

    sortie = io.StringIO()
    ecrivain = csv.writer(sortie, delimiter=";")
    ecrivain.writerow(["Période", libelle])
    ecrivain.writerow([])
    ecrivain.writerow(["Produit", "Quantité vendue", "Montant (FCFA)"])
    for ligne in lignes:
        ecrivain.writerow(
            [securiser_csv(ligne["nom"]), ligne["quantite"], round(ligne["total"])]
        )
    ecrivain.writerow(
        [
            "Total",
            sum(l["quantite"] for l in lignes),
            round(sum(l["total"] for l in lignes)),
        ]
    )

    # Le "\ufeff" permet à Excel d'afficher correctement les accents
    contenu = "\ufeff" + sortie.getvalue()
    nom_fichier = f"rapport_{periode}_{debut.isoformat()}.csv"

    return Response(
        contenu,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{nom_fichier}"'
        },
    )


if __name__ == "__main__":
    app.run(debug=True)