# SARI IIIF Clip Search

## About

A library to index images based on IIIF URLs and enable semantic free text search based on [CLIP](https://github.com/openai/CLIP).

## Usage

### Extract image features

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

#### SPARQL mode example

```bash
python src/build.py \
    --mode SPARQL \
    --imageQuery "PREFIX dcterms: <http://purl.org/dc/terms/ PREFIX la: <https://linked.art/ns/terms/> SELECT ?iiif_url WHERE { ?service a la:DigitalService ; dcterms:conformsTo <http://iiif.io/api/image> ; la:access_point ?iiif_url .}  ORDER BY ?iiif_url LIMIT 100" \
    --endpoint http://example.org/sparql \
    --dataDir ./myFeatures
```

#### CSV mode example

```bash
python src/build.py \
    --mode CSV \
    --csvFile /path/to/csv/file.csv \
    --dataDir ./myFeatures
```

#### Parameters

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

## Acknowledgements

This code is based on [Unsplash Image Search
](https://github.com/haltakov/natural-language-image-search) by [Vladimir Haltakov](https://github.com/haltakov), which in turn is inspired by [Beyond tags and entering the semantic search era on images with OpenAI CLIP](https://towardsdatascience.com/beyond-tags-and-entering-the-semantic-search-era-on-images-with-openai-clip-1f7d629a9978) by [Ramsri Goutham Golla](https://twitter.com/ramsri_goutham), [Alph, The Sacred River](https://github.com/thoppe/alph-the-sacred-river) by [Travis Hoppe](https://twitter.com/metasemantic) and [Unsplash](https://unsplash.com/). [OpenAI's CLIP](https://github.com/openai/CLIP) is the driving model behind both.
