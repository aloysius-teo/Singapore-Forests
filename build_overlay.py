#!/usr/bin/env python3
"""Rebuild the biomass overlay PNG from the source raster.

Reads band 1 of the EPSG:3414 raster, applies the viridis colour ramp,
and saves a transparent RGBA PNG with exact WGS84 bounds.

Dependencies: rasterio, numpy, Pillow, pyproj
"""
import os
import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer

SRC = "biomass_Singapore_2023.tif"
OUT_PNG = "data/biomass_overlay.png"
OUT_BOUNDS = "data/biomass_overlay_bounds.txt"
NODATA = -1
AGB_MAX = 300.0
SCALE = 2  # 1 = full res, 2 = half res

RAMP = [
    (0.00, (68, 1, 84)),   (0.10, (72, 40, 120)),  (0.20, (62, 74, 137)),
    (0.30, (49, 104, 142)), (0.40, (38, 130, 142)), (0.50, (31, 158, 137)),
    (0.60, (53, 183, 121)), (0.70, (110, 206, 88)), (0.80, (181, 222, 43)),
    (0.90, (253, 231, 37)), (1.00, (253, 231, 37)),
]

def _build_lut():
    lut = np.zeros((65536, 4), dtype=np.uint8)
    for v in range(0, 1954):
        t = max(0.0, min(1.0, min(v, 300) / AGB_MAX))
        c = (253, 231, 37)
        for i in range(1, len(RAMP)):
            if t <= RAMP[i][0]:
                a, b = RAMP[i - 1], RAMP[i]
                f = (t - a[0]) / (b[0] - a[0])
                c = tuple(int(round(a[1][k] + (b[1][k] - a[1][k]) * f)) for k in range(3))
                break
        lut[v] = (*c, 255)
    return lut

LUT = _build_lut()

with rasterio.open(SRC) as src:
    data = src.read(1)
    bounds = src.bounds

    to_4326 = Transformer.from_crs("EPSG:3414", "EPSG:4326", always_xy=True)
    west, south = to_4326.transform(bounds.left, bounds.bottom)
    east, north = to_4326.transform(bounds.right, bounds.top)

    idx = np.clip(data, 0, 65535).astype(np.uint16)
    rgba = LUT[idx]
    rgba[data == NODATA] = [0, 0, 0, 0]

    img = Image.fromarray(rgba, "RGBA")
    if SCALE > 1:
        img = img.resize((img.width // SCALE, img.height // SCALE), Image.NEAREST)
    img.save(OUT_PNG, "PNG", optimize=True)

    with open(OUT_BOUNDS, "w") as f:
        f.write(f"{south:.8f},{west:.8f},{north:.8f},{east:.8f}")

    mb = os.path.getsize(OUT_PNG) / (1024 * 1024)
    print(f"✓ {OUT_PNG} — {img.width}×{img.height}, {mb:.1f} MB")
    print(f"  bounds: [{south:.8f}, {west:.8f}] to [{north:.8f}, {east:.8f}]")
