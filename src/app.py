from sariIiifClipSearch import Images
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
    images=Images(
        dataDir=dataDir,
        mode=Images.MODE_SPARQL,
        imageQuery=imageQuery,
        endpoint=endpoint)
    images.queryImages()
    images.downloadImages()
    images.processImages()
    print("OK")

if __name__ == "__main__":
    run()
    