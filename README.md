# SARI IIIF CLIP Search

  * [About](#about)
  * [Query Service](#query-service)
    + [REST API](#rest-api)
    + [SPARQL Endpoint](#sparql-endpoint)
  * [Extract image features](#extract-image-features)
    + [SPARQL mode example](#sparql-mode-example)
    + [CSV mode example](#csv-mode-example)
    + [Parameters](#parameters)
  * [REST API Swagger](#rest-api-swagger)
  * [Acknowledgements](#acknowledgements)

## About

A library to index images based on IIIF URLs and enable semantic free text search based on [CLIP](https://github.com/openai/CLIP).

## Query Service

CLIP Search can be used as a service that can be queried through a simple REST API or through (pseudo) SPARQL.
The repository contains a Docker Compose configuration to run it as a service.

Make a copy of the provided `.env.example` file

```bash
cp .env.example .env
```

Adjust the values in your `.env` file as required. The `CLIP_DATA_DIRECTORY` should point to a directory containing the extracted CLIP features. You can either use one of those provided in `precomputedFeatures` or you can extract your own using the provided `build.py` script.

Run the service using `docker-compose up -d`. The service is now reachable at `http://localhost:5000` (using the default port). Note that the service takes some time to start up as it initialises the CLIP model.

### REST API

The REST API is accessible at `/query`, e.g. `http://localhost:5000/query`. 

To query the search with a string, use the `str` parameter.

e.g. `http://localhost:5000/query?str=Airplane`

Returns:
```json
[
    {
        score: 0.2553620934486389,
        imageId: "3ce3913927093bdad714f65ad44c542796268206",
        url: "https://www.e-manuscripta.ch/zuzneb/i3f/v20/1582208",
        link: "https://www.e-manuscripta.ch/zuzneb/i3f/v20/1582208/full/1000,/0/default.jpg"
    },
    {
        score: 0.2505139708518982,
        imageId: "b75557df7b30f9f16e5506b8e45ccba9837b1bd0",
        url: "https://www.e-manuscripta.ch/zuzneb/i3f/v20/1582203",
        link: "https://www.e-manuscripta.ch/zuzneb/i3f/v20/1582203/full/1000,/0/default.jpg"
    },
    ...
]
```

Optional supported parameters are `minScore` to specify the minimum score the results should have, and `limit` to specify the maximum results to return.

e.g. `http://localhost:5000/query?str=a%20group%20of%20people&minScore=0.29&limit=3`

Returns
```json
[
    {
        score: 0.3113684058189392,
        imageId: "2026e9190cfe333b95623f11bf5f4d0218b7dbfd",
        url: "https://bso-iiif.swissartresearch.net/iiif/2/nb-480729",
        link: "https://bso-iiif.swissartresearch.net/iiif/2/nb-480729/full/1000,/0/default.jpg"
    },
    {
        score: 0.3020486831665039,
        imageId: "0894f033eb159ddd2e3b076745c9ebe629583362",
        url: "https://bso-iiif.swissartresearch.net/iiif/2/nb-479221",
        link: "https://bso-iiif.swissartresearch.net/iiif/2/nb-479221/full/1000,/0/default.jpg"
    },
    {
        score: 0.2966747283935547,
        imageId: "74417f49133656ef9277089f9b1f924e693a6d92",
        url: "https://bso-iiif.swissartresearch.net/iiif/2/nb-479256",
        link: "https://bso-iiif.swissartresearch.net/iiif/2/nb-479256/full/1000,/0/default.jpg"
    }
]
```

### SPARQL Endpoint

The service includes a PSARQL (pseudo SPARQL) endpoint for querying it within SPARQL environments. It lends itself to integrating it via a SERVICE clause.

The example query below illustrates the supported features:

```SPARQL
        PREFIX  clip: <https://service.swissartresearch.net/clip/>
        SELECT ?iiif ?score WHERE { 
            ?request a clip:Request ;
                clip:queryString "A mountain lake" ;
                clip:minScore "0.2" ;
                clip:score ?score ;
                clip:iiifUrl ?iiif .
        } LIMIT 10
```
## Extract image features

To use the CLIP Search with a custom collection of images, the `build.py` script found in `src` can be used.
The script operates either in SPARQL mode or in CSV mode.

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

### SPARQL mode example

```bash
python src/build.py \
    --mode SPARQL \
    --imageQuery "PREFIX dcterms: <http://purl.org/dc/terms/ PREFIX la: <https://linked.art/ns/terms/> SELECT ?iiif_url WHERE { ?service a la:DigitalService ; dcterms:conformsTo <http://iiif.io/api/image> ; la:access_point ?iiif_url .}  ORDER BY ?iiif_url LIMIT 100" \
    --endpoint http://example.org/sparql \
    --dataDir ./myFeatures
```

### CSV mode example

```bash
python src/build.py \
    --mode CSV \
    --csvFile /path/to/csv/file.csv \
    --dataDir ./myFeatures
```

### Parameters

```
    --mode: The mode of operation. Either SPARQL or CSV.
    --imageQuery: The SPARQL query to retrieve the IIIF image URLs. Required in SPARQL mode.
    --endpoint: The SPARQL endpoint to query. Required in SPARQL mode.
    --csvFile: The path to the CSV file. Required in CSV mode
    --dataDir: The path to the directory where the features will be stored.
    --iiifColumn: The name of the column containing the IIIF image URLs. Optional, defaults to iiif_url.
    --threads: The number of threads to use for downloading images. Optional, defaults to 16.
    --batchSize: The number of images to process in one batch. Optional, defaults to 64.
```

## REST API Swagger

```swagger
swagger: "2.0"
info:
  description: "This is a sample server Petstore server.  You can find out more about     Swagger at [http://swagger.io](http://swagger.io) or on [irc.freenode.net, #swagger](http://swagger.io/irc/).      For this sample, you can use the api key `special-key` to test the authorization     filters."
  version: "1.0.0"
  title: "IIIF CLIP Search"
host: "petstore.swagger.io"
schemes:
- "http"
paths:
  /query:
    get:
      summary: "Query the CLIP search"
      produces:
      - "application/json"
      parameters:
      - name: "str"
        in: "query"
        description: "A string to query the index with"
        required: true
        type: "string"
      - name: "minSore"
        in: "query"
        description: "The minimum score of the returned results"
        type: "number"
        required: false
        default: 0.2
      - name: "limit"
        in: "query"
        description: "The maximum number of results to return"
        default: 10
        required: false
        type: "integer"
        
      responses:
        "200":
          description: "successful operation"
          schema:
            type: "array"
            items:
              $ref: "#/definitions/queryResponse"
        "500":
          description: "An error occured"
definitions:
  queryResponse:
    type: "object"
    properties:
      url:
        type: "string"
      score:
        type: "integer"
```

## Acknowledgements

This code is based on [Unsplash Image Search
](https://github.com/haltakov/natural-language-image-search) by [Vladimir Haltakov](https://github.com/haltakov), which in turn is inspired by [Beyond tags and entering the semantic search era on images with OpenAI CLIP](https://towardsdatascience.com/beyond-tags-and-entering-the-semantic-search-era-on-images-with-openai-clip-1f7d629a9978) by [Ramsri Goutham Golla](https://twitter.com/ramsri_goutham), [Alph, The Sacred River](https://github.com/thoppe/alph-the-sacred-river) by [Travis Hoppe](https://twitter.com/metasemantic) and [Unsplash](https://unsplash.com/). [OpenAI's CLIP](https://github.com/openai/CLIP) is the driving model behind both.
