# geonode-demo

Projet d'apprentissage: implémentation du standard OGC CSW (recherche/découverte de données spatiales) via GeoNode, avec visualisation de données (tables, cartes...) dans une interface custom.

## Architecture

Stack hybride:

- **GeoServer** — stack OGC classique (WMS/WFS/WCS/CSW via pycsw), source de vérité pour la découverte et l'accès standard.
- **GeoParquet + COG** (couche secondaire, cloud-native) — stockage objet (MinIO en local) pour l'analytique rapide et les previews:
  - Vecteur → GeoParquet, requêté via **DuckDB** (extension spatial).
  - Raster → Cloud Optimized GeoTIFF, servi en tuiles dynamiques via **TiTiler**.
- **Traefik** — reverse proxy / routing pour tous les services.
- Frontend: app standalone externe qui consomme les endpoints OGC de GeoNode (structure et choix de librairies à définir dans une étape séparée).

## Structure du repo

```
geonode-demo/
├── docker-compose.yml       # orchestration des services
├── .env.example             # variables d'environnement (ports, credentials, domaines)
├── infra/
│   └── traefik/             # config statique/dynamique Traefik
├── data/
│   ├── raw/                 # jeux de données source (vecteur + raster)
│   └── scripts/             # scripts de conversion (COG, GeoParquet) et d'ingestion
└── docs/
    └── architecture.md      # détail des choix d'architecture et étapes
```

## Étapes du projet

Voir [docs/architecture.md](docs/architecture.md) pour le détail des grandes étapes d'infrastructure.
