import time, urllib.request, urllib.parse, json

t0 = time.time()
base = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
filter_expr = "Collection/Name eq 'SENTINEL-2' and contains(Name, 'MSIL2A') and OData.CSC.Intersects(area=geography'SRID=4326;POINT(80.74 17.98)')"
params = {"$filter": filter_expr, "$top": "2", "$orderby": "ContentDate/Start desc"}
url = f"{base}?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"Time taken: {time.time()-t0:.2f}s, Items: {len(data.get('value', []))}")
except Exception as e:
    print(f"Time taken: {time.time()-t0:.2f}s, Error: {e}")
