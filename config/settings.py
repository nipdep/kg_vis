from decouple import config

PAGE_TITLE = "Idea Graph Visualizer"
PAGE_ICON = config("PAGE_ICON")
PAGE_IMAGE = config("PAGE_IMAGE")
GITHUB_REPO = config("GITHUB_REPO")
DESCRIPTION = config("DESCRIPTION")

IDEA_ENDPOINT = "http://localhost:3030/idea_kg/sparql"

PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "idea": "http://www.semanticweb.org/idea/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dct": "http://purl.org/dc/terms/",
    "cso": "http://cso.kmi.open.ac.uk/schema/cso#",
    "doco": "http://purl.org/spar/doco/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "fabio": "http://purl.org/spar/fabio/",
    "deo": "http://purl.org/spar/deo/",
    "cito": "http://purl.org/spar/cito/",
    "po":    "http://purl.org/spar/po/",
    "amo":   "http://purl.org/spar/amo/",
    "c4o":   "http://purl.org/spar/c4o/",
    "xml":   "http://www.w3.org/XML/1998/namespace",
    "bibo":  "http://purl.org/ontology/bibo/",
    "expo":  "http://www.hozo.jp/owl/EXPOApr19.xml/",
    "prism": "http://prismstandard.org/namespaces/1.2/basic/",
    "semsur": "http://purl.org/semsur/"
}

FABIO_WORK = "http://purl.org/spar/fabio/Work"
FABIO_NS   = "http://purl.org/spar/fabio/"
RDF_TYPE   = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

STRUCTURE_PREFIXES = [
    "http://purl.org/spar/deo/",
    "http://purl.org/spar/doco/",
    "http://purl.org/spar/fabio/",
    "http://purl.org/spar/po/",
    "http://purl.org/ontology/bibo/",
]
ARGUMENT_PREFIXES = [
    "http://purl.org/spar/amo/",
    "http://www.semanticweb.org/idea/",
    "http://purl.org/semsur/",
]
