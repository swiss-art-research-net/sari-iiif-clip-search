from sariIiifClipSearch import Images, Query

dataDir = '/precomputedFeatures/bso/'

def run():

    clipQuery=Query(
        dataDir=dataDir
    )
    queryStrings = ["A mountain", "A lake", "People"]
    for queryString in queryStrings:
        print(queryString, clipQuery.query(queryString, numResults=3))

if __name__ == "__main__":
    run()
    