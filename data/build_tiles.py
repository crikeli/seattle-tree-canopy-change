"""
Pre-renders each NAIP COG (docs/cogs/naip_<year>.tif) into a standard
XYZ raster tile pyramid (WebP, EPSG:3857) instead of relying on the
browser to decode/reproject the whole COG client-side.

Why: georaster-layer-for-leaflet does that decoding + resampling in pure
JS on the main thread, which is the real source of the "lag" toggling
NAIP layers - not the network. A pre-rendered tile pyramid lets the
browser load NAIP the same way it loads any other basemap: small,
independently-cacheable image tiles via a plain Leaflet L.tileLayer, no
client-side raster math at all.

Zoom range comes from rio-tiler's own resolution-based estimate
(dataset is already 5m/px - decimated for the canopy analysis, not
native NAIP resolution), extended one level past native for smoother
zooming.

Usage:
    python data/build_tiles.py
"""

import os

import morecantile
from rio_tiler.io import Reader

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(os.path.dirname(DATA_DIR), "docs")
TILES_DIR = os.path.join(DATA_DIR, "tiles")

YEARS = [2013, 2023]
EXTRA_ZOOM = 1  # one level past native resolution, for smoother zoom-in


def build_year(year: int) -> int:
    cog_path = os.path.join(DOCS_DIR, "cogs", f"naip_{year}.tif")
    out_count = 0
    with Reader(cog_path) as reader:
        minzoom = reader.minzoom
        maxzoom = reader.maxzoom + EXTRA_ZOOM
        bounds = reader.get_geographic_bounds(reader.tms.rasterio_geographic_crs)
        print(f"{year}: native zoom {reader.minzoom}-{reader.maxzoom}, "
              f"generating {minzoom}-{maxzoom}")

        for z in range(minzoom, maxzoom + 1):
            tiles = list(reader.tms.tiles(*bounds, zooms=[z]))
            for t in tiles:
                try:
                    img = reader.tile(t.x, t.y, z)
                except Exception:
                    continue  # tile outside actual raster extent (bbox corner)
                if img.mask is not None and img.mask.max() == 0:
                    continue  # fully nodata tile, skip
                content = img.render(img_format="WEBP")
                out_path = os.path.join(TILES_DIR, str(year), str(z), str(t.x), f"{t.y}.webp")
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "wb") as f:
                    f.write(content)
                out_count += 1
            print(f"  z={z}: {len(tiles)} candidate tiles")
    return out_count


def main() -> None:
    total = 0
    for year in YEARS:
        total += build_year(year)
    print(f"\nWrote {total} tiles total under {TILES_DIR}")


if __name__ == "__main__":
    main()
