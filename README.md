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
trust a color-coded number. The two COGs (~43-45MB each) are hosted on
[Cloudflare R2](https://www.cloudflare.com/developer-platform/products/r2/)
rather than committed to this repo, and the page streams them via real
HTTP range requests (`parseGeoraster(url)`, not a pre-fetched
`arrayBuffer`) - toggling a year only pulls the tiles for whatever you're
currently looking at, not the whole file.

## Repo layout

```
notebooks/
  tree_canopy_change.ipynb   # the full, executed analysis - STAC search, mosaic
                              # alignment, radiometric fix, zonal stats, COG export
data/
  build_static_site.py       # renders docs/index.html from the notebook's outputs
  seattle_cra.geojson        # Seattle Community Reporting Area boundaries
  canopy_change_map.png      # sanity-check choropleth from the notebook
docs/
  index.html                 # the deployed static site
  canopy_change.geojson      # per-neighborhood canopy % + change, from the notebook
environment.yml
```

The two NAIP COGs (`naip_2013.tif`, `naip_2023.tif`) are built by the
notebook but not committed here - they're hosted on Cloudflare R2 (see
above) and git-ignored locally.

## Setup

```bash
conda env create -f environment.yml
conda activate seattle-tree-canopy-change
```

```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/tree_canopy_change.ipynb
python data/build_static_site.py
```

## Stack

pystac-client + planetary-computer (NAIP access via STAC), rasterio,
rioxarray, rio-cogeo, geopandas - Leaflet + georaster-layer-for-leaflet
for the deployed static site, Esri World Imagery for basemap context,
Cloudflare R2 for imagery hosting.
