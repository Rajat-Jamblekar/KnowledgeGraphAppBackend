import networkx as nx

class MedicalGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_relationship(self, source, relation, target):
        self.graph.add_node(source)
        self.graph.add_node(target)
        self.graph.add_edge(source, target, label=relation)

    def query_diagnosis(self, symptom):
        return [
            target for target, edge in self.graph[symptom].items()
            if edge.get("label") == "indicates"
        ]

    def query_treatments(self, disease):
        return [
            target for target, edge in self.graph[disease].items()
            if edge.get("label") == "treated by"
        ]

    def query_specialists(self, condition):
        results = []
        for target, edge in self.graph[condition].items():
            if edge.get("label") in ["managed by", "prescribed by"]:
                results.append(target)
        return results

    def export_graph(self):
        nodes = [{"id": n} for n in self.graph.nodes()]
        links = [{"source": u, "target": v, "label": d["label"]} for u, v, d in self.graph.edges(data=True)]
        return {"nodes": nodes, "links": links}
