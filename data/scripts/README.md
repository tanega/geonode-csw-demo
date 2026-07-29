# Scripts de conversion / ingestion

À implémenter à l'étape 3 (storage cloud-natif):

- `to_cog.sh` — conversion raster → Cloud Optimized GeoTIFF (`gdal_translate` + `gdaladdo`)
- `to_geoparquet.sh` — conversion vecteur → GeoParquet (`ogr2ogr` / `gpq`)
- `upload_minio.sh` — upload des fichiers convertis vers le bucket MinIO
