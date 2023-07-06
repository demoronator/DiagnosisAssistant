import HPO_explorer
import orphanet_db
import re
import requests
from flask import Flask, jsonify, request, render_template
from waitress import serve

app = Flask(__name__)
hpo = HPO_explorer.HPO_explorer("hp.obo")
o = orphanet_db.orphanet_db()
key_pt = open("phenotagger.key", "r").read().strip()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search", methods=["GET"])
def search():
    query = " ".join(sorted(request.args.get("q", "").lower().split()))
    limit = request.args.get("limit", None, type=int)
    results = hpo.find_terms(query.strip(), limit=limit)
    return jsonify(results)


@app.route("/superterms", methods=["GET"])
def superterms():
    term_id = request.args.get("term_id", "")
    distance = request.args.get("distance", 1, type=int)
    results = hpo.get_superterms(term_id, distance=distance)
    return jsonify(results)


@app.route("/disorders", methods=["GET"])
def disorders():
    hpo_ids = request.args.get("hpo_ids", "").upper()
    hpo_ids = re.sub(r"\s+", "", hpo_ids)
    s = frozenset(hpo_ids.split(","))
    result = o.get_disorders(s)
    d: dict[str, list] = {}
    for row in result:
        t = f"ORPHA:{row[0]} {row[1]}"
        if t not in d:
            d[t] = []
        d[t].append((row[2], row[3], row[4]))

    return jsonify(d)


@app.route("/biotag", methods=["POST"])
def biotag():
    data = request.get_json()
    host = "https://phenotagger-dot-diagnosis-assistant-app.uw.r.appspot.com"

    try:
        response = requests.post(
            f"{host}/biotag", json=data, headers={"Authorization": f"Bearer {key_pt}"}
        )
        terms = response.json()

    except Exception as e:
        print(e)
        return jsonify({"error": "PhenoTagger is not available."})

    l = []
    for term in terms:
        l.append([term[2], hpo.get_termname(term[2])])

    return jsonify(l)


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=5000)
