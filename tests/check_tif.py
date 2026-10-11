import os
import rasterio
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIF_PATH = os.path.join(BASE_DIR, 'outputs', 'manganese_prospectivity.tif')
if not os.path.exists(TIF_PATH):
    TIF_PATH = 'outputs/manganese_prospectivity.tif'

try:
    with rasterio.open(TIF_PATH) as src:
        print('TIFF opened successfully!')
        print('Shape:', src.shape)
        print('Bounds:', src.bounds)
        print('CRS:', src.crs)
        print('Transform:', src.transform)
        # Sample at known mine
        px, py = src.index(441089.328, 2426904.204)
        val = src.read(1, window=((px, px+1), (py, py+1)))
        print(f'Pixel at mine: row={px}, col={py}, value={val[0,0]}')
except Exception as e:
    print('Rasterio check:', e)
