import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'clip'))

import csv
import math
import numpy as np
import pandas as pd
import torch
import urllib.request
from clip import clip
from hashlib import blake2b
from pathlib import Path
from PIL import Image
from SPARQLWrapper import SPARQLWrapper, JSON
from multiprocessing.pool import ThreadPool

IDENTIFIERCOLUMN = 'localIdentifier'

class Images:
    
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
        batchSize=16):
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

    def downloadImages(self):
        urls = []
        with open(self.imageCSV, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                urls.append(row[self.iiifColumn])

        pool = ThreadPool(self.threads)
        pool.map(self._downloadImage, urls)

    def processImages(self):

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
        # Execute Query
        sparql = SPARQLWrapper(self.endpoint)
        sparql.setQuery(self.imageQuery)
        sparql.setReturnFormat(JSON)
        try:
            results = sparql.query().convert()
        except Exception as e:
            return e
        # Save to CSV
        self._saveSPARQLResultToCSV(results)
        
        return True
        
class Query:

    def __init__(self, *, dataDir, imageCSV=None, iiifColumn="iiif_url"):
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

    def query(self, queryString, *, numResults=5):
        with torch.no_grad():
            # Encode and normalize the description using CLIP
            textEncoded = self.model.encode_text(clip.tokenize(queryString).to(self.device))
            textEncoded /= textEncoded.norm(dim=-1, keepdim=True)

        # Retrieve the description vector and the photo vectors
        textFeatures = textEncoded.cpu().numpy()

        # Compute the similarity between the descrption and each photo using the Cosine similarity
        similarities = list((textFeatures @ self.imageFeatures.T).squeeze(0))

        # Sort the images by their similarity score
        bestImages = sorted(zip(similarities, range(self.imageFeatures.shape[0])), key=lambda x: x[0], reverse=True)

        # Get the top 10 images
        results = []
        for image in bestImages[:numResults]:
            result = {
                'score': image[0],
                'imageId': self.imageIDs.iloc[image[1]]['image_id'],
            }
            result['url'] = self.imageData.loc[self.imageData[IDENTIFIERCOLUMN] == result['imageId']][self.iiifColumn].values[0]
            results.append(result)
        return results
