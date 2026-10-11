import urllib.parse
import urllib.request
import json

filter_expr = "Collection/Name eq 'SENTINEL-2' and contains(Name, 'MSIL2A') and OData.CSC.Intersects(area=geography'SRID=4326;POINT(80.7450 17.9820)') and ContentDate/Start ge 2025-01-01T00:00:00.000Z"
params = {'$filter': filter_expr, '$top': '2', '$orderby': 'ContentDate/Start desc'}
url = 'https://catalogue.dataspace.copernicus.eu/odata/v1/Products?' + urllib.parse.urlencode(params)
headers = {'User-Agent': 'TestClient/2.0', 'Accept': 'application/json'}
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=12) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print('Status:', resp.status, 'Total items:', len(data.get('value', [])))
        for item in data.get('value', []):
            print('Scene:', item.get('Name'), 'Date:', item.get('ContentDate', {}).get('Start'))
except Exception as e:
    print('Error:', e)
