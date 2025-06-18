from flask import Flask, request, jsonify
from flask_cors import CORS
import networkx as nx
import pandas as pd
import io

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests for frontend testing

# Initialize directed graph for medical knowledge
graph = nx.DiGraph()

# Helper function to add relationship to graph
def add_relationship(source, relation, target):
    # Add nodes with type property if missing
    if not graph.has_node(source):
        graph.add_node(source, type="Unknown")
    if not graph.has_node(target):
        graph.add_node(target, type="Unknown")

    # Add edge with relation attribute
    graph.add_edge(source, target, relation=relation)

# Endpoint to add single concept relationships
@app.route('/add-concept', methods=['POST'])
def add_concept():
    data = request.json
    try:
        # Expect data like: source, relation, target, and optionally types
        source = data.get('source')
        relation = data.get('relation')
        target = data.get('target')
        source_type = data.get('source_type', "Unknown")
        target_type = data.get('target_type', "Unknown")

        if not source or not relation or not target:
            return jsonify({"error": "source, relation, and target are required"}), 400

        # Add/update nodes with types
        if graph.has_node(source):
            graph.nodes[source]['type'] = source_type
        else:
            graph.add_node(source, type=source_type)

        if graph.has_node(target):
            graph.nodes[target]['type'] = target_type
        else:
            graph.add_node(target, type=target_type)

        # Add edge/relation
        graph.add_edge(source, target, relation=relation)

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
            # Parse JSON content
            data = request.get_json(force=True, silent=True)
            # Expect data format: list of {source, relation, target, source_type, target_type}
            if not data:
                # fallback: parse content as json string
                import json
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
                    if graph.has_node(source):
                        graph.nodes[source]['type'] = source_type
                    else:
                        graph.add_node(source, type=source_type)

                    if graph.has_node(target):
                        graph.nodes[target]['type'] = target_type
                    else:
                        graph.add_node(target, type=target_type)

                    graph.add_edge(source, target, relation=relation)

            return jsonify({"message": "JSON data uploaded and processed successfully"})

        elif filename.endswith('.csv'):
            # Use pandas to parse CSV
            df = pd.read_csv(io.BytesIO(content))
            # Expect columns: source, relation, target, optional source_type, target_type
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

                if graph.has_node(source):
                    graph.nodes[source]['type'] = source_type
                else:
                    graph.add_node(source, type=source_type)

                if graph.has_node(target):
                    graph.nodes[target]['type'] = target_type
                else:
                    graph.add_node(target, type=target_type)

                graph.add_edge(source, target, relation=relation)

            return jsonify({"message": "CSV data uploaded and processed successfully"})
        else:
            return jsonify({"error": "Unsupported file type"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint to query diagnoses for a given symptom
@app.route('/query/diagnoses-for-symptom', methods=['GET'])
def diagnoses_for_symptom():
    symptom = request.args.get('symptom')
    if not symptom:
        return jsonify({"error": "symptom parameter is required"}), 400

    try:
        # Find all diseases where symptom 'indicates' disease
        diseases = []
        # edges from symptom where relation is 'indicates'
        for nbr in graph.successors(symptom):
            rel = graph.edges[symptom, nbr].get('relation', '').lower()
            if rel == 'indicates' or rel == 'indicate':
                diseases.append(nbr)
        return jsonify({"diseases": diseases})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint to query treatments for a given disease
@app.route('/query/treatments-for-disease', methods=['GET'])
def treatments_for_disease():
    disease = request.args.get('disease')
    if not disease:
        return jsonify({"error": "disease parameter is required"}), 400
    try:
        treatments = []
        for nbr in graph.successors(disease):
            rel = graph.edges[disease, nbr].get('relation', '').lower()
            if rel == 'treated by' or rel == 'treated_by' or rel == 'treated':
                treatments.append(nbr)
        return jsonify({"treatments": treatments})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint to query specialists for a given disease or treatment
@app.route('/query/specialists-for-entity', methods=['GET'])
def specialists_for_entity():
    entity = request.args.get('entity')
    if not entity:
        return jsonify({"error": "entity parameter is required"}), 400
    try:
        specialists = []
        for nbr in graph.successors(entity):
            rel = graph.edges[entity, nbr].get('relation', '').lower()
            # Common relation terms linking to specialists: 'managed by', 'prescribed by'
            if rel in ['managed by', 'managed_by', 'prescribed by', 'prescribed_by']:
                specialists.append(nbr)
        return jsonify({"specialists": specialists})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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