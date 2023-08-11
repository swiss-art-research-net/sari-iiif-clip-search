from sariIiifClipSearch import Query

dataDir = '/precomputedFeatures/bso/'

def run():

    clipQuery=Query(
        dataDir=dataDir
    )
    queryStrings = ["A mountain", "A lake", "People", "A car", "A disaster", "Airplane"]
    for queryString in queryStrings:
        results = clipQuery.query(queryString, numResults=3)
        print(queryString, [d['url'] + '/full/1000,/0/default.jpg' for d in results])

if __name__ == "__main__":
    run()
    