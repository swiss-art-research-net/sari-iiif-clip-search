"""
This script is used to download and process images from a IIIF API. It can operate either in SPARQL or in CSV mode.

In SPARQL mode a SPARQL query and a SPARQL endpoint are required. The query needs to retrieve the IIIF image URLs 
bound to the variable ?iiif_url. If another variable is used, it can be provided via the --iiifColumn option.

In CSV mode the path to a CSV file is required. The CSV file needs to contain the IIIF image URLs in a column named iiif_url.
If another column is used, it can be provided via the --iiifColumn option.

For both modes of operation the path to a directory needs to be specified via the --dataDir option. The script will operate in
this directory. A subdirectory named 'images' will be created and the images will be downloaded to this directory. The
features will be computed and stored in a subdirectory named 'features'.

For publishing the extracted features, the downloaded images can be deleted from the directory when the script has finished. 
The final features will be stored in the files features.npy and imageIds.csv. For publishing all other files in the features
directory can be deleted. Retaining them locally can however be useful to speed up later processing.

Usage:

SPARQL mode:

    python build.py \
        --mode SPARQL \
        --imageQuery "PREFIX dcterms: <http://purl.org/dc/terms/ PREFIX la: <https://linked.art/ns/terms/> SELECT ?iiif_url WHERE { ?service a la:DigitalService ; dcterms:conformsTo <http://iiif.io/api/image> ; la:access_point ?iiif_url .}  ORDER BY ?iiif_url LIMIT 100" \
        --endpoint http://example.org/sparql \
        --dataDir ./myFeatures

CSV mode:

    python build.py \
        --mode CSV \
        --csvFile /path/to/csv/file.csv \
        --dataDir ./myFeatures

Parameters:
    --mode: The mode of operation. Either SPARQL or CSV.
    --imageQuery: The SPARQL query to retrieve the IIIF image URLs. Required in SPARQL mode.
    --endpoint: The SPARQL endpoint to query. Required in SPARQL mode.
    --csvFile: The path to the CSV file. Required in CSV mode
    --dataDir: The path to the directory where the features will be stored.
    --iiifColumn: The name of the column containing the IIIF image URLs. Optional, defaults to iiif_url.
    --threads: The number of threads to use for downloading images. Optional, defaults to 16.
    --batchSize: The number of images to process in one batch. Optional, defaults to 64.

"""


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

def build(options):
    from sariIiifClipSearch import Images

    if options['mode'] == 'SPARQL':
        mode = Images.MODE_SPARQL
    elif options['mode'] == 'CSV':
        mode = Images.MODE_CSV
    else:
        raise Exception('Unknown mode: ' + options['mode'])

    if mode == Images.MODE_SPARQL:
        imageQuery = options['imageQuery']
        endpoint = options['endpoint']

        imageProcessor = Images(
            mode=mode,
            dataDir=options['dataDir'],
            iiifColumn=options['iiifColumn'],
            imageQuery=options['imageQuery'],
            endpoint=options['endpoint'],
            threads=options['threads'],
            batchSize=options['batchSize']
        )
    elif mode == Images.MODE_CSV:
        csvFile = options['csvFile']

        imageProcessor = Images(
            mode=mode,
            dataDir=options['dataDir'],
            iiifColumn=options['iiifColumn'],
            imageCSV=options['csvFile'],
            threads=options['threads'],
            batchSize=options['batchSize']
        )
    
    if mode == Images.MODE_SPARQL:
        print("Querying images")
        try:
            imageProcessor.queryImages()
        except Exception as e:
            sys.exit(e)

    print("Downloading images")
    imageProcessor.downloadImages()

    print("Processing images")
    imageProcessor.processImages()

    print("Done.")

if __name__ == "__main__":
    import sys
    options = {}

    for i, arg in enumerate(sys.argv[1:]):
        if arg.startswith("--"):
            if not sys.argv[i + 2].startswith("--"):
                options[arg[2:]] = sys.argv[i + 2]
            else:
                print("Malformed arguments")
                sys.exit(1)

    if not 'mode' in options:
        print("The mode (CSV or SPARQL) is required")
        sys.exit(1)

    if not 'dataDir' in options:
        print("The data directory is required")
        sys.exit(1)

    if options['mode'] == 'CSV':
        if not 'csvFile' in options:
            print("The CSV file is required")
            sys.exit(1)
    elif options['mode'] == 'SPARQL':
        if not 'imageQuery' in options:
            print("The SPARQL image query is required")
            sys.exit(1)
        if not 'endpoint' in options:
            print("The SPARQL endpoint is required")
            sys.exit(1)
    else: 
        print("The mode needs to be either CSV or SPARQL")
        sys.exit(1)

    if not 'iiifColumn' in options:
        options['iiifColumn'] = 'iiif_url'

    if not 'threads' in options:
        options['threads'] = 16
    else:
        options['threads'] = int(options['threads'])

    if not 'batchSize' in options:
        options['batchSize'] = 64
    else:
        options['batchSize'] = int(options['batchSize'])

    build(options)
    