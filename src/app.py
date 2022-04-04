from sariIiifClipSearch import ClipSearch
from pathlib import Path

dataDir = '/workdir/data/'
imageQuery = """
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX la: <https://linked.art/ns/terms/>
SELECT ?iiif_url WHERE {
    ?service a la:DigitalService ;
        dcterms:conformsTo <http://iiif.io/api/image> ;
        la:access_point ?iiif_url .
} 
ORDER BY ?iiif_url
LIMIT 100
"""
endpoint = 'http://blazegraph:8080/blazegraph/sparql'

def run():
    clipSearch=ClipSearch(
        dataDir=dataDir,
        mode=ClipSearch.MODE_SPARQL,
        imageQuery=imageQuery,
        endpoint=endpoint)
    clipSearch.queryImages()
    clipSearch.downloadImages()
    clipSearch.processImages()
    print("OK")

if __name__ == "__main__":
    run()
    