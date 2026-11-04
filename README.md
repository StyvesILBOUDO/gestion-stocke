\# Gestion de stock



Application web de gestion de stock pour une petite boutique, réalisée avec Flask et SQLite dans un but d'apprentissage.



\## Fonctionnalités



\- Connexion sécurisée (mots de passe hachés, sessions)

\- Ajout, modification et suppression de produits

\- Enregistrement des ventes avec mise à jour automatique du stock

\- Refus des ventes lorsque le stock est insuffisant

\- Historique des ventes avec calcul des totaux



\## Technologies



Python 3, Flask, SQLite, HTML/CSS



\## Installation



1\. Cloner le dépôt puis créer l'environnement virtuel :

python -m venv venv

venv\\Scripts\\activate

pip install flask



2\. Créer la base de données avec deux produits d'exemple :

python init\_db.py



3\. Créer un utilisateur :



python creer\_utilisateur.py



4\. Lancer l'application :



python app.py



5\. Ouvrir http://127.0.0.1:5000



\## Structure du projet



\- `app.py` : routes et logique de l'application

\- `schema.sql` : structure de la base de données

\- `init\_db.py` : initialisation de la base

\- `creer\_utilisateur.py` : création d'un compte utilisateur

\- `templates/` : pages HTML



\## Pistes d'amélioration



\- Protection contre les attaques CSRF

\- Gestion de plusieurs rôles (administrateur, vendeur)

\- Tests automatisés



\## Auteur



Styves ILBOUDO, étudiant en Licence 3 Informatique

