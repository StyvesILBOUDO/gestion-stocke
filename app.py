from flask import Flask

app = Flask(__name__)

@app.route("/")
def accueil():
    return "Gestion de stock : ça marche !"

if __name__ == "__main__":
    app.run(debug=True)