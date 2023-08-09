import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'clip'))

import csv
import math
import numpy as np
import pandas as pd
import torch
import urllib.request
import requests
from clip import clip
from hashlib import blake2b
from pathlib import Path
from PIL import Image
from SPARQLWrapper import SPARQLWrapper, JSON
from multiprocessing.pool import ThreadPool

IDENTIFIERCOLUMN = 'localIdentifier'

class Images:
    """
    This class can be used to download and process images, either based on a CSV file or a SPARQL query.
    """
    
    MODE_SPARQL = 1
    MODE_CSV = 2

    def __init__(self, *, 
        mode=MODE_CSV, 
        endpoint=None, 
        iiifColumn="iiif_url",
        imageCSV=None,
        dataDir, 
        imageQuery=None, 
        threads=16,
        batchSize=64):

        """
        Instantiate and initialise the class.

        Parameters:
            mode: The mode of the class. Can be either MODE_CSV or MODE_SPARQL. Defaults to MODE_CSV.
            imageCSV: The path to the CSV file containing the images. Required if mode is MODE_CSV.
            imageQuery: The SPARQL query to execute to get the images. Required if mode is MODE_SPARQL.
            iiifColumn: The column in the CSV file, or the variable in the SPARQL query that contains the IIIF URL. Defaults to "iiif_url".
            endpoint: The SPARQL endpoint to query. Required if mode is MODE_SPARQL.
            dataDir: The directory to save the images and features to.
            threads: The number of threads to use when downloading images. Defaults to 16.
            batchSize: The batch size of images to process on the GPU. Defaults to 16.

        Usage Example:

            # Initialise in CSV mode. 
            # The images.csv file must contain a column with the name 'iiif_url' that contains the IIIF URL of the images.
            # If another column name is used, it must be specified in the iiifColumn parameter.
            images = Images(mode=Images.MODE_CSV, imageCSV='images.csv', dataDir='data')

            # Initialise in SPARQL mode.
            # The SPARQL query must return a column with the name 'iiif_url' that contains the IIIF URL of the images.
            # If another column name is used, it must be specified in the iiifColumn parameter.
            # The SPARQL endpoint must be specified in the endpoint parameter.
            imageQuery = \"""
                PREFIX dcterms: <http://purl.org/dc/terms/>
                PREFIX la: <https://linked.art/ns/terms/>
                SELECT ?iiif_url WHERE {
                    ?service a la:DigitalService ;
                    dcterms:conformsTo <http://iiif.io/api/image> ;
                    la:access_point ?iiif_url .
                } 
                ORDER BY ?iiif_url
                LIMIT 100
            \"""
            images = Images(mode=Images.MODE_SPARQL, imageQuery=imageQuery, endpoint='http://example.org/sparql', dataDir='data')
        """ 

        if not dataDir:
            raise Exception("dataDir is required")
        if mode == self.MODE_SPARQL:
            if not imageQuery:
                raise Exception("imageQuery is required in SPARQL mode")
            if not endpoint:
                raise Exception("endpoint is required in SPARQL mode")

        self.mode = mode
        self.iiifColumn = iiifColumn
        self.threads = threads
        self.batchSize = batchSize

        self.imageDir = Path(dataDir) / 'images'
        self.featuresDir = Path(dataDir) / 'features'
        if not self.imageDir.exists():
            self.imageDir.mkdir(parents=True)

        if not self.featuresDir.exists():
            self.featuresDir.mkdir(parents=True)
        
        if not imageCSV:
            self.imageCSV = Path(dataDir) / 'images.csv'
        else:
            self.imageCSV = Path(imageCSV)
        
        if self.mode == self.MODE_SPARQL:
            self.imageQuery = imageQuery
            self.endpoint = endpoint

    def _customHash(self, inputString):
        h = blake2b(digest_size=20)
        h.update(inputString.encode())
        return h.hexdigest()

    def _downloadImage(self, iiifUrl):
        width = 640
        url = iiifUrl + '/full/' + str(width) + ',/0/default.jpg'
        photoPath = self._getFilePathForImage(iiifUrl)

        # Only download a photo if it doesn't exist
        if not photoPath.exists():
            try:
                urllib.request.urlretrieve(url, photoPath)
            except:
                # Catch the exception if the download fails for some reason
                print(f"Cannot download {url}")
                pass

    def _getFilePathForImage(self, iiifUrl):
        photoId = self._customHash(iiifUrl)
        photoPath = Path(self.imageDir) / (photoId + ".jpg")
        return photoPath

    def _saveSPARQLResultToCSV(self, sparqlResult):
        # Save to CSV
        fieldnames = sparqlResult['head']['vars'] + [IDENTIFIERCOLUMN]
        with open(self.imageCSV, 'w') as f:
            csvWriter = csv.DictWriter(f, fieldnames=fieldnames)
            csvWriter.writeheader()
            for result in sparqlResult['results']['bindings']:
                row = {}
                for field in fieldnames:
                    if field in result:
                        row[field] = result[field]['value']
                # Add local filename of image
                row[IDENTIFIERCOLUMN] = self._customHash(row[self.iiifColumn])
                csvWriter.writerow(row)

    def addIdentifiersToCsv(self):
        """
        Populate a column that contains the local identifiers of the images to the csv file.
        """
        rows = []
        with open(self.imageCSV, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row[IDENTIFIERCOLUMN] = self._customHash(row[self.iiifColumn])
                rows.append(row)
        fieldnames = rows[0].keys()
        with open(self.imageCSV, 'w') as f:
            csvWriter = csv.DictWriter(f, fieldnames=fieldnames)
            csvWriter.writeheader()
            for row in rows:
                csvWriter.writerow(row)
    
    def downloadImages(self):
        """
        Download the images from the CSV file.
        If SPARQL mode is used, the images need to be queried first and will then be automatically savedin a CSV file.
        """
        urls = []
        with open(self.imageCSV, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                urls.append(row[self.iiifColumn])

        pool = ThreadPool(self.threads)
        pool.map(self._downloadImage, urls)

    def processImages(self):
        """
        Compute the features of the images that have been downloaded.
        """

        def compute_clip_features(photos_batch):
            # Load all the photos from the files
            photos = [Image.open(photo_file) for photo_file in photos_batch]
            
            # Preprocess all photos
            photos_preprocessed = torch.stack([preprocess(photo) for photo in photos]).to(device)

            with torch.no_grad():
                # Encode the photos batch to compute the feature vectors and normalize them
                photos_features = model.encode_image(photos_preprocessed)
                photos_features /= photos_features.norm(dim=-1, keepdim=True)

            # Transfer the feature vectors back to the CPU and convert to numpy
            return photos_features.cpu().numpy()

        imageFiles = list(self.imageDir.glob('*.jpg'))
        print(f"Found {len(imageFiles)} images")

        # Load the open CLIP model
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model, preprocess = clip.load("ViT-B/32", device=device)
        
        batches = math.ceil(len(imageFiles) / self.batchSize)

        for i in range(batches):
            print(f"Processing batch {i+1}/{batches}")

            batchIdsPath = self.featuresDir / f"{i:010d}.csv"
            batchFeaturesPath = self.featuresDir / f"{i:010d}.npy"

            # Only do the processing if the batch wasn't processed yet
            if not batchFeaturesPath.exists():
                try:
                    # Get the batch of images
                    batchFiles = imageFiles[i*self.batchSize : (i+1)*self.batchSize]

                    # Compute the features for the batch and save to a numpy file
                    batchFeatures = compute_clip_features(batchFiles)
                    np.save(batchFeaturesPath, batchFeatures)

                    # Save the batch ID to a CSV file
                    photoIDs = [imageFile.name.split(".")[0] for imageFile in batchFiles]
                    photoIDsData = pd.DataFrame(photoIDs, columns=["image_id"])
                    photoIDsData.to_csv(batchIdsPath, index=False)
                except:
                    # Catch the exception if the processing fails for some reason
                    print(f"Cannot process batch {i}")

        featuresList = [np.load(featuresFile) for featuresFile in sorted(self.featuresDir.glob("*.npy"))]
        features = np.concatenate(featuresList)
        np.save(self.featuresDir / "features.npy", features)

        imageIDs = pd.concat([pd.read_csv(idsFile) for idsFile in sorted(self.featuresDir.glob("*.csv"))])
        imageIDs.to_csv(self.featuresDir / "imageIds.csv", index=False)

        return True

    def queryImages(self):
        """"
        Query the images from the SPARQL endpoint and save the result to a CSV file.
        """
        # Execute Query
        sparql = SPARQLWrapper(self.endpoint)
        sparql.setQuery(self.imageQuery)
        sparql.setReturnFormat(JSON)
        try:
            results = sparql.query().convert()
        except Exception as e:
            raise e
        # Save to CSV
        self._saveSPARQLResultToCSV(results)
        
        return True
        
class Query:
    """
    This class can be used to query the previously processed image using CLIP
    """

    MODE_TEXT = 1
    MODE_URL = 2
    MODE_IMAGE = 3

    def __init__(self, *, dataDir, imageCSV=None, iiifColumn="iiif_url"):
        """
        Initialize the query object.
        params:
            dataDir: The directory where the features and image IDs are stored.
            imageCSV: The CSV file containing the image IDs. Only needs to be used if CSV mode has been used to process the images
            iiifColumn: The column in the CSV file or the variable in the SPARQL query containing the IIIF URLs.
        """
        if not dataDir:
            raise Exception("dataDir is required")

        self.iiifColumn = iiifColumn
        self.imageDir = Path(dataDir) / 'images'
        self.featuresDir = Path(dataDir) / 'features'
        if not imageCSV:
            self.imageCSV = Path(dataDir) / 'images.csv'
        else:
            self.imageCSV = Path(imageCSV)

        self.imageFeatures = np.load(self.featuresDir / 'features.npy')
        self.imageIDs = pd.read_csv(self.featuresDir / 'imageIds.csv')
        self.imageData = pd.read_csv(self.imageCSV)

        # Load the open CLIP model
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)

    def query(self, queryInput, *, mode=MODE_TEXT, numResults=5, minScore=0.2):
        """
        Query the images using the query string.
        params:
            queryInput: The query string to be used for the query.
            numResults: The number of results to be returned. Default is 5.
        """
        if mode == self.MODE_TEXT:
            with torch.no_grad():
                # Encode and normalize the description using CLIP
                textEncoded = self.model.encode_text(clip.tokenize(queryInput).to(self.device))
                textEncoded /= textEncoded.norm(dim=-1, keepdim=True)

            # Retrieve the description vector and the photo vectors
            textFeatures = textEncoded.cpu().numpy()

            # Compute the similarity between the descrption and each photo using the Cosine similarity
            similarities = list((textFeatures @ self.imageFeatures.T).squeeze(0))
        elif mode == self.MODE_URL or mode == self.MODE_IMAGE:
            if mode == self.MODE_URL:
                # Load the image from the URL into a PIL image
                images = [Image.open(requests.get(queryInput, stream=True).raw)]
            elif mode == self.MODE_IMAGE:
                # Image is passed as PIL image in queryInput
                images = [queryInput]

            imagesPreprocessed = torch.stack([self.preprocess(image) for image in images]).to(self.device)

            with torch.no_grad():
                # Encode the photos batch to compute the feature vectors and normalize them
                photoFeatures = self.model.encode_image(imagesPreprocessed)
                photoFeatures /= photoFeatures.norm(dim=-1, keepdim=True)
            
            photoFeatures = photoFeatures.cpu().numpy()

            similarities = list((photoFeatures @ self.imageFeatures.T).squeeze(0))

        # Sort the images by their similarity score
        bestImages = sorted(zip(similarities, range(self.imageFeatures.shape[0])), key=lambda x: x[0], reverse=True)

        # Get the top images
        results = []
        for image in bestImages[:numResults]:
            score = float(image[0])
            if score < minScore:
                break
            imageId = self.imageIDs.iloc[image[1]]['image_id']
            imageUrl = self.imageData.loc[self.imageData[IDENTIFIERCOLUMN] == imageId][self.iiifColumn].values[0]
            result = {
                'score': score,
                'imageId': str(imageId),
                'url': str(imageUrl)
            }
            results.append(result)
        return results
