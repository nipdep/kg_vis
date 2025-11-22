from core.query_builder import build_query 
from core.sparql_client import sparql 


def get_all_works(endpoint):
    query = build_query("""
        SELECT DISTINCT ?work WHERE { 
            ?work rdf:type ?type .
            ?type rdfs:subClassOf* fabio:Work .                
        }
        LIMIT 50
        """)
    
    return sparql(endpoint, query) 


def get_work_triples(endpoint, work_uri):
    query = build_query(f"""
    SELECT ?s ?p ?o WHERE {{
        <{work_uri}> ?p ?o .
        BIND(<{work_uri}> AS ?s)
    }}
    """)
    return sparql(endpoint, query)