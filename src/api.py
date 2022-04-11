import json
import os
from flask import Flask, Response, request
from rdflib.term import Variable, URIRef, Literal
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
    if 'str' in request.values:
        queryString = request.values['str']
        if 'limit' in request.values:
            limit = int(request.values['limit'])
        else:
            limit = DEFAULT_NUMRESULTS
        if 'minScore' in request.values:
            minScore = float(request.values['minScore'])
        else:
            minScore = DEFAULT_MINSCORE
        result = queryWithString(queryString, minScore=minScore, numResults=limit)
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
    if not 'queryString' in request:
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
    results = clipQuery.query(request['queryString'], minScore=minScore, numResults=numResults)
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

def queryWithString(queryString, *, minScore=DEFAULT_MINSCORE, numResults=DEFAULT_NUMRESULTS):
    results = clipQuery.query(queryString, numResults=numResults, minScore=minScore)
    for result in results:
        result['link'] = result['url'] + '/full/640,/0/default.jpg'
    return results

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)