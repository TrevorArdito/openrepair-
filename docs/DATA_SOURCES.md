# Data sources

| Data | Source | License | How it gets in |
|---|---|---|---|
| VIN decoding, makes, models | [NHTSA vPIC API](https://vpic.nhtsa.dot.gov/api/) | US government work (public domain) | Live on demand, cached in our DB |
| Recalls | [api.nhtsa.gov recalls](https://www.nhtsa.gov/nhtsa-datasets-and-apis#recalls) | Public domain | Live on demand, cached 7 days; `refresh` script |
| Owner complaints | [api.nhtsa.gov complaints](https://www.nhtsa.gov/nhtsa-datasets-and-apis#complaints) | Public domain | Live on demand, cached 7 days; `refresh` script |
| TSB index (manufacturer communications) | [NHTSA bulk files](https://www.nhtsa.gov/nhtsa-datasets-and-apis#manufacturer-communications), field list in [TSBS.txt](https://static.nhtsa.gov/odi/ffdd/tsbs/TSBS.txt) | Public domain index | `python -m app.importers.nhtsa tsbs` |
| Community guides/specs | Our users, in their own words | CC BY-SA 4.0 | Website/app |

We store NHTSA's **index and summary** of each bulletin, not the manufacturer's full document.

## Refreshing the data
```bash
cd backend   # or: docker compose exec api ...
python -m app.importers.nhtsa refresh                 # recalls + complaints, all known vehicles
python -m app.importers.nhtsa refresh --force         # ignore the 7-day cache
python -m app.importers.nhtsa tsbs                    # TSBs 2020-now for models in our DB
python -m app.importers.nhtsa tsbs --period 2015-2019 # older bulletins
```
By default the TSB import only keeps bulletins for models already in our database (keeps the
database small enough for free hosting). `--all-models` imports everything (several GB).
