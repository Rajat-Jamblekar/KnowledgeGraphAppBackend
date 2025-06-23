# Medical Knowledge Graph Backend

A Flask-based backend service that manages a medical knowledge graph, allowing storage and querying of medical concepts, their relationships, and supporting smart search capabilities.

## Features

- Build and manage a directed graph of medical knowledge
- Smart search with fuzzy matching and spell correction
- Support for both JSON and CSV data uploads
- RESTful API endpoints for querying medical relationships
- Cross-origin resource sharing (CORS) enabled for frontend integration

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirement.txt
   ```
4. Run the application:
   ```bash
   python app.py
   ```

The server will start at `http://127.0.0.1:5000`

## API Endpoints

### Add a Single Concept
```http
POST http://127.0.0.1:5000/add-concept
Content-Type: application/json

{
    "source": "headache",
    "relation": "indicates",
    "target": "migraine",
    "source_type": "symptom",
    "target_type": "disease"
}
```

### Upload Bulk Data
```http
POST http://127.0.0.1:5000/upload-data
```
Supports both JSON and CSV file uploads with the following structure:
- JSON: Array of objects with `source`, `relation`, `target`, `source_type`, and `target_type`
- CSV: File with columns for `source`, `relation`, `target`, `source_type`, and `target_type`

### Query Endpoints

#### Get Diagnoses for a Symptom
```http
GET http://127.0.0.1:5000/query/diagnoses-for-symptom?symptom=headache
```
Returns possible diagnoses/diseases that the given symptom may indicate.

#### Get Treatments for a Disease
```http
GET http://127.0.0.1:5000/query/treatments-for-disease?disease=migraine
```
Returns treatments associated with the specified disease.

#### Get Specialists for an Entity
```http
GET http://127.0.0.1:5000/query/specialists-for-entity?entity=migraine
```
Returns medical specialists who can manage/treat the specified condition.

#### Get Full Graph Data
```http
GET http://127.0.0.1:5000/graph
```
Returns the complete knowledge graph data for visualization, including all nodes and their relationships.

## Features

### Smart Search
The application includes smart search capabilities:
- Fuzzy matching for imperfect matches
- Spell correction for medical terms
- Case-insensitive searching

### Graph Structure
- Nodes represent medical concepts (symptoms, diseases, treatments, specialists)
- Edges represent relationships between concepts
- Directed graph allows for proper representation of medical relationships

## Dependencies

- Flask: Web framework
- Flask-CORS: Cross-origin resource sharing
- NetworkX: Graph management
- pandas: Data processing
- scikit-learn: Machine learning utilities
- thefuzz: Fuzzy string matching
- python-Levenshtein: Fast string matching
- autocorrect: Spell correction

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.