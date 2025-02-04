import sys
import base64
import json
import os
import re
from flask import Flask, Response, request
from io import BytesIO
from rdflib.term import Variable, URIRef, Literal
from PIL import Image
from sariIiifClipSearch import Query
from sariSparqlParser import parser

try:
  dataDir = os.environ['CLIP_DATA_DIRECTORY']
except:
  print("CLIP_DATA_DIRECTORY environment variable not set.")
  sys.exit(1)

app = Flask(__name__)

clipQuery=Query(
    dataDir=dataDir
)

DEFAULT_MINSCORE=0.2
DEFAULT_NUMRESULTS=100

@app.route('/')
def index():
    return 'Server Works!'

@app.route('/query', methods=['GET', 'POST'])
def query():
    if 'limit' in request.values:
        limit = int(request.values['limit'])
    else:
        limit = DEFAULT_NUMRESULTS
    if 'minScore' in request.values:
        minScore = float(request.values['minScore'])
    else:
        minScore = DEFAULT_MINSCORE

    if 'str' in request.values:
        queryString = request.values['str']
        result = queryWithString(queryString, minScore=minScore, numResults=limit)
        return Response(json.dumps(result), mimetype='application/json')
    elif 'url' in request.values:
        queryUrl = request.values['url']
        result = queryWithUrl(queryUrl, minScore=minScore, numResults=limit)
        return Response(json.dumps(result), mimetype='application/json')
    elif 'image' in request.values:
        queryImage = decodeImageFromUrlString(request.values['image'])
        result = queryWithImage(queryImage, minScore=minScore, numResults=limit)
        return Response(json.dumps(result), mimetype='application/json')
    return Response('{"status": "OK"}', mimetype='application/json')

@app.route('/sparql', methods=['GET', 'POST'])
def sparql():
    if 'query' in request.values:
        query = request.values['query']
        response = processSparqlQuery(query)
        return Response(json.dumps(response), mimetype='application/json')
    
    return Response('{"status": "OK"}', mimetype='application/json')

def createSparqlResponse(query, request, results):

    def getDataTypeForValue(value):
        if isinstance(value, int):
            return "http://www.w3.org/2001/XMLSchema#integer"
        if isinstance(value, float):
            return "http://www.w3.org/2001/XMLSchema#float"
        return "http://www.w3.org/2001/XMLSchema#string"
    
    def getTypeForField(key):
        if 'url' in key:
            return 'uri'
        return 'literal'

    p = parser()
    parsedQuery = p.parseQuery(query)

    response = {}
    response['head'] = {
        "vars": parsedQuery['select']
    }
    bindings = []

    for result in results:
        row = {}
        for key, variable in request['select'].items():
            if variable in parsedQuery['select']:
                row[variable] = {
                    "value": result[key],
                    "type": getTypeForField(key),
                    "datatype": getDataTypeForValue(result[key])
                }
        bindings.append(row)
    response['results'] = {'bindings': bindings}
    return response

def decodeImageFromUrlString(urlString): 
    """
    Decodes an image from a base64 encoded URL string and returns it as a PIL Image

    >>> base64String = 'data:image/jpeg;base64,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'
    >>> image = decodeImageFromUrl(base64String)
    """
    imageString = re.sub('^data:image/.+;base64,', '', urlString)
    image = Image.open(BytesIO(base64.b64decode(str(imageString))))
    return image

def error(message):
  """
  Generate a JSON error object
  """
  return {"error": message}

def extractRequestFromSparqlQuery(query):
    """
    Given an SPARQL query this function extracts the request.
    It does so by looking at the triples contained in the WHERE clause.
    Only a single request is suported
  
    Consider the following SPARQL query:

        PREFIX  clip: <https://service.swissartresearch.net/clip/>
        SELECT ?iiif ?score WHERE { 
            ?request a clip:Request ;
                clip:queryString "A mountain lake" ;
                clip:minScore "0.2" ;
                clip:score ?score ;
                clip:iiifUrl ?iiif .
        } LIMIT 10
    """
    p = parser()
    try:
        parsedQuery = p.parseQuery(query)
    except Exception as e:
        return {'error': str(e)}
    
    def addSelect(request, key, map):
        if not 'select' in request:
            request['select'] = {}
        request['select'][key] = map
        return request

    def addOption(request, option, value):
        if not 'options' in request:
            request['options'] = {}
        request['options'][option] = value
        return request

    def getValueWithoutPrefix(value):
        if value.startswith("pname_pname_"):
            return value[45:-2]
        prefix = 'https://service.swissartresearch.net/clip/'
        return value[len(prefix):]

    request = {}

    for triple in parsedQuery['where']:
        if triple['s']['type'] == Variable and getValueWithoutPrefix(triple['o']['value']) == 'Request':
            request['variable'] = triple['s']['value']
            # Process only first request encountered
            break
    for triple in parsedQuery['where']:
        if triple['s']['value'] == request['variable']:
            if getValueWithoutPrefix(triple['p']['value']) == 'queryString' and triple['o']['type'] == Literal:
                request['queryString'] = triple['o']['value']
            elif getValueWithoutPrefix(triple['p']['value']) == 'queryURL' and triple['o']['type'] == URIRef:
                request['queryURL'] = triple['o']['value']
            elif getValueWithoutPrefix(triple['p']['value']) == 'queryImage' and triple['o']['type'] == Literal:
                request['queryImage'] = triple['o']['value']
            elif getValueWithoutPrefix(triple['p']['value']) == 'minScore' and triple['o']['type'] == Literal:
                request = addOption(request, 'minScore', float(triple['o']['value']))
            elif getValueWithoutPrefix(triple['p']['value']) == 'iiifUrl' and triple['o']['type'] == Variable:
                request = addSelect(request, 'url', triple['o']['value'])
            elif getValueWithoutPrefix(triple['p']['value']) == 'score' and triple['o']['type'] == Variable:
                request = addSelect(request, 'score', triple['o']['value'])

    if 'limitOffset' in parsedQuery and parsedQuery['limitOffset']:
        if 'limit' in parsedQuery['limitOffset']:
            request = addOption(request, 'numResults', int(parsedQuery['limitOffset']['limit']))

    return request

def processSparqlQuery(query):
  """
  Accepts a parsed SPARQL query, extracts and processes the requests and returns a SPARQL response.
  """
  request = extractRequestFromSparqlQuery(query)
  result = queryWithRequest(request)
  response = createSparqlResponse(query, request, result)
  return response

def queryWithRequest(request):
    if not 'queryString' in request and not 'queryURL' in request and not 'queryImage' in request:
        return error('No query string provided')
    if 'options' in request:
        if 'minScore' in request['options']:
            minScore = float(request['options']['minScore'])
        else:
            minScore = DEFAULT_MINSCORE
        if 'numResults' in request['options']:
            numResults = int(request['options']['numResults'])
        else:
            numResults = DEFAULT_NUMRESULTS
    if 'queryString' in request:
        results = clipQuery.query(request['queryString'], minScore=minScore, numResults=numResults)
    elif 'queryURL' in request:
        results = clipQuery.query(request['queryURL'], mode=Query.MODE_URL, minScore=minScore, numResults=numResults)
    elif 'queryImage' in request:
        queryImage = decodeImageFromUrlString(request['queryImage'])
        results = clipQuery.query(queryImage, mode=Query.MODE_IMAGE, minScore=minScore, numResults=numResults)
    filteredResults = []
    if 'select' in request:
        for result in results:
            filteredResult = {}
            for key, value in result.items():
                if key in request['select']:
                    filteredResult[key] = value
            filteredResults.append(filteredResult)
        return filteredResults
    else:
        return results

def queryWithImage(image, *, minScore=DEFAULT_MINSCORE, numResults=DEFAULT_NUMRESULTS):
    results = clipQuery.query(image, mode=Query.MODE_IMAGE, numResults=numResults, minScore=minScore)
    for result in results:
        result['link'] = result['url'] + '/full/640,/0/default.jpg'
    return results

def queryWithString(queryString, *, minScore=DEFAULT_MINSCORE, numResults=DEFAULT_NUMRESULTS):
    results = clipQuery.query(queryString, numResults=numResults, minScore=minScore)
    for result in results:
        result['link'] = result['url'] + '/full/640,/0/default.jpg'
    return results

def queryWithUrl(queryUrl, *, minScore=DEFAULT_MINSCORE, numResults=DEFAULT_NUMRESULTS):
    results = clipQuery.query(queryUrl, mode=Query.MODE_URL, numResults=numResults, minScore=minScore)
    for result in results:
        result['link'] = result['url'] + '/full/640,/0/default.jpg'
    return results

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)