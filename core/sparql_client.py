import aiohttp
import asyncio
from SPARQLWrapper import SPARQLWrapper, JSON
import logging


# async def async_sparql(endpoint, query):
#     async with aiohttp.ClientSession() as session:
#         async with session.post(
#             endpoint,
#             data={"query": query},
#             headers={"Accept": "application/sparql-results+json"}
#         ) as resp:
#             data = await resp.json()
#             return data["results"]["bindings"]

async def async_sparql(endpoint, query: str):
    headers = {
        "Accept": "application/sparql-results+json",
        "Content-Type": "application/sparql-query"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(endpoint, headers=headers, data=query) as resp:
            text = await resp.text()

            # ---- DEBUG OUTPUT ----
            print("SPARQL STATUS:", resp.status)
            print("SPARQL MIMETYPE:", resp.headers.get("Content-Type"))
            print("SPARQL RESPONSE TEXT:", text[:500])
            # -----------------------

            if resp.status != 200:
                logging.error(f"[Fuseki ERROR {resp.status}] {text}")
                return []

            try:
                return (await resp.json())["results"]["bindings"]
            except Exception as e:
                logging.error("JSON decode failed")
                logging.error(text)
                raise e

def sparql(endpoint, query):
    return asyncio.run(async_sparql(endpoint, query))

def execute_query_convert(endpoint: str, query: str):
    try:
        sparql = SPARQLWrapper(endpoint)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        return results["results"]["bindings"]
    except Exception as e:
        logging.error(query)
        logging.error(e)
        return []
