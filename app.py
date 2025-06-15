from flask import Flask, request, jsonify
from flask_cors import CORS
from graph_manager import MedicalGraph

app = Flask(__name__)
CORS(app)
graph = MedicalGraph()

@app.route("/add_concept", methods=["POST"])
def add_concept():
    data = request.json
    source = data["source"]
    relation = data["relation"]
    target = data["target"]
    graph.add_relationship(source, relation, target)
    return jsonify({"status": "success"}), 200

@app.route("/query_diagnosis", methods=["GET"])
def query_diagnosis():
    symptom = request.args.get("symptom")
    results = graph.query_diagnosis(symptom)
    return jsonify(results)

@app.route("/query_treatments", methods=["GET"])
def query_treatments():
    disease = request.args.get("disease")
    results = graph.query_treatments(disease)
    return jsonify(results)

@app.route("/query_specialists", methods=["GET"])
def query_specialists():
    condition = request.args.get("condition")
    results = graph.query_specialists(condition)
    return jsonify(results)

@app.route("/graph_data", methods=["GET"])
def graph_data():
    return jsonify(graph.export_graph())

if __name__ == "__main__":
    app.run(debug=True)
