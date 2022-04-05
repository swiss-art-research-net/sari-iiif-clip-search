import json
import os
from flask import Flask, Response, request
from sariIiifClipSearch import Query


try:
  dataDir = os.environ['CLIP_DATA_DIRECTORY']
except:
  print("CLIP_DATA_DIRECTORY environment variable not set.")
  sys.exit(1)

app = Flask(__name__)

clipQuery=Query(
    dataDir=dataDir
)

@app.route('/')
def index():
    return 'Server Works!'

@app.route('/query', methods=['GET', 'POST'])
def query():
    if 'str' in request.values:
        queryString = request.values['str']
        result = queryWithString(queryString)
        return Response(json.dumps(result), mimetype='application/json')
    return Response('{"status": "OK"}', mimetype='application/json')
    
def queryWithString(queryString):
    results = clipQuery.query(queryString, numResults=3)
    for result in results:
        result['link'] = result['url'] + '/full/1000,/0/default.jpg'
    return results

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)