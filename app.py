from flask import Flask, request, jsonify
from flask_cors import CORS
import networkx as nx
import pandas as pd
import io

# Libraries for smart search capabilities
from thefuzz import process  # For fuzzy string matching
from autocorrect import Speller  # For basic spell correction

# Initialize Flask app and allow cross-origin requests (for frontend communication)
app = Flask(__name__)
CORS(app)

# Initialize a directed graph to represent the medical knowledge network
graph = nx.DiGraph()

# Initialize spell corrector for English
spell = Speller(lang='en')


def all_node_names():
    """
    Returns a list of all node names in lowercase.
    Useful for standardizing lookups.
    """
    return [node.lower() for node in graph.nodes]


def smart_lookup(query, threshold=80):
    """
    Perform a smart lookup of a node name using spell correction and fuzzy matching.

    Parameters:
        query (str): The user input to be matched to a graph node.
        threshold (int): Fuzzy match score threshold (0–100).

    Returns:
        str or None: Matched node name from the graph if found, else None.
    """
    if not query:
        return None

    query = query.strip().lower()
    corrected = spell(query)
    node_list = list(graph.nodes)

    # Try exact match (case-insensitive)
    for node in node_list:
        if node.lower() == corrected:
            return node

    # Try fuzzy match
    match, score = process.extractOne(corrected, node_list, scorer=process.default_scorer)
    if score >= threshold:
        return match

    return None


def add_relationship(source, relation, target, source_type="Unknown", target_type="Unknown"):
    """
    Adds a directed relationship between two concepts in the graph.

    Parameters:
        source (str): Source concept name.
        relation (str): Type of relationship (e.g., "indicates", "treated by").
        target (str): Target concept name.
        source_type (str): Optional type label for the source node.
        target_type (str): Optional type label for the target node.
    """
    source = source.strip().lower()
    target = target.strip().lower()
    relation = relation.strip().lower()

    # Add source node with type
    if graph.has_node(source):
        graph.nodes[source]['type'] = source_type
    else:
        graph.add_node(source, type=source_type)

    # Add target node with type
    if graph.has_node(target):
        graph.nodes[target]['type'] = target_type
    else:
        graph.add_node(target, type=target_type)

    # Add the directed edge with the relationship type
    graph.add_edge(source, target, relation=relation)


@app.route('/add-concept', methods=['POST'])
def add_concept():
    """
    Endpoint to add a single relationship (edge) between two concepts.

    Expected JSON payload:
    {
        "source": "headache",
        "relation": "indicates",
        "target": "migraine",
        "source_type": "Symptom",
        "target_type": "Disease"
    }
    """
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


@app.route('/upload-data', methods=['POST'])
def upload_data():
    """
    Endpoint to upload a CSV or JSON file containing multiple relationships.

    JSON format: List of dicts, each with keys: source, relation, target, source_type, target_type
    CSV format: Columns must include: source, relation, target
    """
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['file']
        filename = file.filename.lower()
        content = file.read()

        if filename.endswith('.json'):
            import json
            # Try parsing as JSON
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
            df = pd.read_csv(file)  # FIXED LINE

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


@app.route('/query/diagnoses-for-symptom', methods=['GET'])
def diagnoses_for_symptom():
    """
    Endpoint to retrieve possible diseases for a given symptom (with smart lookup).

    Query Parameter:
        symptom (str): The symptom to search for.

    Returns:
        JSON list of diseases and the matched node.
    """
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
    except Exception:
        return jsonify({"error": "Could not find what you searched for."}), 404


@app.route('/query/treatments-for-disease', methods=['GET'])
def treatments_for_disease():
    """
    Endpoint to retrieve possible treatments for a given disease (with smart lookup).

    Query Parameter:
        disease (str): The disease to search for.

    Returns:
        JSON list of treatments and the matched node.
    """
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
    except Exception:
        return jsonify({"error": "Could not find what you searched for."}), 404


@app.route('/query/specialists-for-entity', methods=['GET'])
def specialists_for_entity():
    """
    Endpoint to retrieve relevant specialists for a given disease or treatment (smart search).

    Query Parameter:
        entity (str): The disease or treatment to search for.

    Returns:
        JSON list of specialists and the matched node.
    """
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
    except Exception:
        return jsonify({"error": "Could not find what you searched for."}), 404


@app.route('/graph', methods=['GET'])
def get_graph():
    """
    Endpoint to retrieve the full graph structure (nodes and edges).

    Returns:
        JSON with 'nodes' and 'edges' lists.
    """
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


# Run the Flask app in debug mode
if __name__ == '__main__':
    app.run(debug=True)
