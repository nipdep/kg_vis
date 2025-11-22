from config.settings import PREFIXES

def prefix_block():
    lines = [f"PREFIX {p}: <{uri}>" for p, uri in PREFIXES.items()]
    return "\n".join(lines)

def build_query(body: str):
    return prefix_block() + "\n\n" + body.strip()


def replace_prefixes_if_uri(uri: str) -> str:
    if not uri or not isinstance(uri, str):
        return uri
    for pref, ns in PREFIXES.items():
        if uri.startswith(ns):
            return f"{pref}:{uri[len(ns):]}"
    return uri

def is_resource(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


