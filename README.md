# Seattle Tree Canopy Change (Demo)

An independent estimate of how Seattle's tree canopy changed between 2013
and 2023, built entirely from open data: two dates of USDA NAIP aerial
imagery, ten years apart, diffed with the same method across the whole
city. King County's own tree canopy layer only covers a single year
(2021), so there's no official dataset to directly compare against - this
project computes both dates itself, the same way, so the comparison is
at least internally consistent.

**Live site: https://crikeli.github.io/seattle-tree-canopy-change/**

## What this is - and isn't

Citywide NDVI-based canopy estimate for 2013 and 2023, per Seattle's 53
official Community Reporting Areas. **Not** an official canopy assessment
- see Seattle's own published 2016-2021 canopy study (cited in the
notebook and the site's About tab) for that. The canopy threshold is
calibrated against a published external reference (~28% citywide canopy),
not an absolute physical measurement, and the analysis runs at 5m
resolution (decimated from NAIP's native 0.6-1m) - fine for
neighborhood-level change, not individual trees.

**Finding:** citywide tree canopy fell from an estimated 28.0% (2013) to
24.4% (2023) - a 3.6 percentage point loss over the decade, concentrated
in the Central District / Capitol Hill / First Hill corridor, which saw
substantial infill development and upzoning over that period.

## Real data problems hit along the way

**NAIP's two dates don't share a grid.** 2013 NAIP is 1m resolution,
2023 is 0.6m - merging each year's tiles independently let `rasterio`
pick a different output extent per year, making the two mosaics
impossible to difference. Fixed by computing one canonical bounds/resolution
from the city polygon once, and passing it explicitly to both years'
`rasterio.merge` calls.

**A real systematic radiometric offset between acquisitions.** Even after
fixing the grid, raw NDVI means differed sharply between years on the
*identical* footprint (2013 mean 0.038 vs 2023 mean 0.135) - a genuine
multi-date NAIP calibration difference, not a bug, confirmed by checking
that valid-pixel counts matched almost exactly between years. Fixed with
per-year z-score normalization, with the canopy cutoff itself calibrated
once against Seattle's published ~28% citywide figure.

**Water inference by NDVI threshold was unreliable.** Switched to King
County's real natural-shoreline boundary layer to clip Puget Sound and
Lake Washington out of the land area instead of inferring water from
NDVI.

## The site streams real satellite imagery, not just a choropleth

Beyond the per-neighborhood change map, the site lets you toggle the
actual NAIP aerial photos for 2013 and 2023 on top of the map (with
opacity sliders) to visually inspect where canopy loss happened, not just
trust a color-coded number.

**First version of this streamed the raw COGs client-side** via
`georaster-layer-for-leaflet` (`parseGeoraster(url)` + HTTP range
requests) - technically working, but visibly laggy on toggle, because
that library decodes and reprojects every pixel in pure JS on the
browser's main thread. The COG's own structure (512x512 internal tiling,
3 overview levels) wasn't the bottleneck; the client-side raster math
was.

**Real fix:** `data/build_tiles.py` pre-renders each COG into a standard
WebP XYZ tile pyramid (zoom 10-15, matching the data's actual 5m
resolution plus one level for smooth zooming - under 2,000 tiles total,
~22MB for both years combined, smaller than either original COG) using
[rio-tiler](https://cogeotiff.github.io/rio-tiler/). The site then loads
NAIP the exact same way it loads the Esri basemap - a plain Leaflet
`L.tileLayer` - with zero client-side raster decoding. Both are hosted on
[Cloudflare R2](https://www.cloudflare.com/developer-platform/products/r2/)
rather than committed to this repo.

## Repo layout

```
notebooks/
  tree_canopy_change.ipynb   # the full, executed analysis - STAC search, mosaic
                              # alignment, radiometric fix, zonal stats, COG export
data/
  build_static_site.py       # renders docs/index.html from the notebook's outputs
  build_tiles.py              # pre-renders each COG into a WebP tile pyramid (rio-tiler)
  seattle_cra.geojson        # Seattle Community Reporting Area boundaries
  canopy_change_map.png      # sanity-check choropleth from the notebook
docs/
  index.html                 # the deployed static site
  canopy_change.geojson      # per-neighborhood canopy % + change, from the notebook
environment.yml
```

The two NAIP COGs (`naip_2013.tif`, `naip_2023.tif`) and the tile pyramid
built from them (`data/tiles/`) are produced locally but not committed
here - they're hosted on Cloudflare R2 (see above) and git-ignored.

## Setup

```bash
conda env create -f environment.yml
conda activate seattle-tree-canopy-change
```

```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/tree_canopy_change.ipynb
python data/build_tiles.py
python data/build_static_site.py
```

Uploading the tile pyramid to R2 (after `build_tiles.py`) is a separate
step - `aws s3 sync data/tiles s3://<bucket>/tiles --endpoint-url
https://<account-id>.r2.cloudflarestorage.com`.

## Stack

pystac-client + planetary-computer (NAIP access via STAC), rasterio,
rioxarray, rio-cogeo, rio-tiler, geopandas - Leaflet for the deployed
static site (plain `L.tileLayer`, no client-side raster decoding), Esri
World Imagery for basemap context, Cloudflare R2 for tile hosting.
