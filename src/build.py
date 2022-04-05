from sariIiifClipSearch import Images, Query

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

    performProcessing = True

    if performProcessing:
        images=Images(
            dataDir=dataDir,
            mode=Images.MODE_SPARQL,
            imageQuery=imageQuery,
            endpoint=endpoint)
        images.queryImages()
        images.downloadImages()
        images.processImages()

    clipQuery=Query(
        dataDir=dataDir
    )
    queryStrings = ["A mountain", "A lake", "People"]
    for queryString in queryStrings:
        print(queryString, clipQuery.query(queryString, numResults=1))

if __name__ == "__main__":
    run()
    