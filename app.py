from flask import Flask, request, jsonify
from flask_cors import CORS
import networkx as nx
import pandas as pd
import io

# Smart search libraries
from thefuzz import process
from autocorrect import Speller

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests for frontend testing

# Initialize directed graph for medical knowledge
graph = nx.DiGraph()
spell = Speller(lang='en')

# Helper: get all node names (lowercase)
def all_node_names():
    return [node.lower() for node in graph.nodes]

# Helper: smart lookup for node name (case, typo, spell)
def smart_lookup(query, threshold=80):
    if not query:
        return None
    query = query.strip().lower()
    corrected = spell(query)
    node_list = list(graph.nodes)
    # Try exact match first (case-insensitive)
    for node in node_list:
        if node.lower() == corrected:
            return node
    # Fuzzy match
    match, score = process.extractOne(corrected, node_list, scorer=process.default_scorer)
    if score >= threshold:
        return match
    return None

# Helper function to add relationship to graph
def add_relationship(source, relation, target, source_type="Unknown", target_type="Unknown"):
    # Normalize for storage
    source = source.strip().lower()
    target = target.strip().lower()
    relation = relation.strip().lower()
    if graph.has_node(source):
        graph.nodes[source]['type'] = source_type
    else:
        graph.add_node(source, type=source_type)
    if graph.has_node(target):
        graph.nodes[target]['type'] = target_type
    else:
        graph.add_node(target, type=target_type)
    graph.add_edge(source, target, relation=relation)

# Endpoint to add single concept relationships
@app.route('/add-concept', methods=['POST'])
def add_concept():
    data = request.json
    try:
        source = data.get('source')
        relation = data.get('relation')
        target = data.get('target')
        source_type = data.get('source_type', "Unknown")
        target_type = data.get('target_type', "Unknown")
        if not source or not relation or not target:
            return jsonify({"error": "source, relation, and target are required"}), 400
        add_relationship(source, relation, target, source_type, target_type)
        return jsonify({"message": "Concept added successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint to upload JSON or CSV data with concepts and relationships
@app.route('/upload-data', methods=['POST'])
def upload_data():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        file = request.files['file']
        filename = file.filename.lower()
        content = file.read()
        if filename.endswith('.json'):
            import json
            data = request.get_json(force=True, silent=True)
            if not data:
                data = json.loads(content)
            if not isinstance(data, list):
                return jsonify({"error": "JSON must contain a list of relationships"}), 400
            for entry in data:
                source = entry.get("source")
                relation = entry.get("relation")
                target = entry.get("target")
                source_type = entry.get("source_type", "Unknown")
                target_type = entry.get("target_type", "Unknown")
                if source and relation and target:
                    add_relationship(source, relation, target, source_type, target_type)
            return jsonify({"message": "JSON data uploaded and processed successfully"})
        elif filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
            if not {'source', 'relation', 'target'}.issubset(df.columns):
                return jsonify({"error": "CSV must contain columns: source, relation, target"}), 400
            for _, row in df.iterrows():
                source = row['source']
                relation = row['relation']
                target = row['target']
                source_type = row.get('source_type', "Unknown")
                target_type = row.get('target_type', "Unknown")
                if not source or not relation or not target:
                    continue
                add_relationship(source, relation, target, source_type, target_type)
            return jsonify({"message": "CSV data uploaded and processed successfully"})
        else:
            return jsonify({"error": "Unsupported file type"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint to query diagnoses for a given symptom (smart search)
@app.route('/query/diagnoses-for-symptom', methods=['GET'])
def diagnoses_for_symptom():
    symptom = request.args.get('symptom')
    if not symptom:
        return jsonify({"error": "symptom parameter is required"}), 400
    try:
        node = smart_lookup(symptom)
        if not node:
            return jsonify({"error": f"No close match found for symptom '{symptom}'"}), 404
        diseases = []
        for nbr in graph.successors(node):
            rel = graph.edges[node, nbr].get('relation', '').lower()
            if rel in ['indicates', 'indicate']:
                diseases.append(nbr)
        return jsonify({"diseases": diseases, "matched_node": node})
    except Exception as e:
        return jsonify({"error": "Could not find what you searched for."}), 404

# Endpoint to query treatments for a given disease (smart search)
@app.route('/query/treatments-for-disease', methods=['GET'])
def treatments_for_disease():
    disease = request.args.get('disease')
    if not disease:
        return jsonify({"error": "disease parameter is required"}), 400
    try:
        node = smart_lookup(disease)
        if not node:
            return jsonify({"error": f"No close match found for disease '{disease}'"}), 404
        treatments = []
        for nbr in graph.successors(node):
            rel = graph.edges[node, nbr].get('relation', '').lower()
            if rel in ['treated by', 'treated_by', 'treated']:
                treatments.append(nbr)
        return jsonify({"treatments": treatments, "matched_node": node})
    except Exception as e:
        return jsonify({"error": "Could not find what you searched for."}), 404

# Endpoint to query specialists for a given disease or treatment (smart search)
@app.route('/query/specialists-for-entity', methods=['GET'])
def specialists_for_entity():
    entity = request.args.get('entity')
    if not entity:
        return jsonify({"error": "entity parameter is required"}), 400
    try:
        node = smart_lookup(entity)
        if not node:
            return jsonify({"error": f"No close match found for entity '{entity}'"}), 404
        specialists = []
        for nbr in graph.successors(node):
            rel = graph.edges[node, nbr].get('relation', '').lower()
            if rel in ['managed by', 'managed_by', 'prescribed by', 'prescribed_by']:
                specialists.append(nbr)
        return jsonify({"specialists": specialists, "matched_node": node})
    except Exception as e:
        return jsonify({"error": "Could not find what you searched for."}), 404

# Endpoint to get full graph data for visualization
@app.route('/graph', methods=['GET'])
def get_graph():
    try:
        nodes = []
        edges = []
        for node, data in graph.nodes(data=True):
            nodes.append({
                "id": node,
                "type": data.get("type", "Unknown")
            })
        for src, tgt, data in graph.edges(data=True):
            edges.append({
                "source": src,
                "target": tgt,
                "relation": data.get("relation", "")
            })
        return jsonify({"nodes": nodes, "edges": edges})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
