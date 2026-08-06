import logging

logger = logging.getLogger(__name__)


def on_dataset_saved(sender, instance, created, **kwargs):
    """
    Mirror every newly-created vector dataset to GeoParquet on MinIO, so
    the cloud-native analytics layer stays populated automatically
    instead of relying on manually running data/scripts/*.sh + the
    hardcoded link_cloud_native_assets.py after each upload.
    """
    if not created or instance.subtype != "vector":
        return

    from uploads_api.tasks import mirror_dataset_to_geoparquet

    mirror_dataset_to_geoparquet.delay(instance.id)
