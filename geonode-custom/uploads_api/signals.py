import logging

logger = logging.getLogger(__name__)


def on_dataset_saved(sender, instance, created, **kwargs):
    """
    On first save of any Dataset (vector or raster):
    - stamp date_type="creation" so the `date` field (already set to
      upload time by GeoNode's own default) reads as a creation date in
      CSW instead of the default "publication" type.
    - record a "data last updated" ExtraMetadata entry: no native
      ResourceBase field can hold a second date alongside `date`, so this
      is set once here (creation time) and left for a curator to update
      by hand later when the underlying data actually changes.

    Vector datasets are additionally mirrored to GeoParquet on MinIO, so
    the cloud-native analytics layer stays populated automatically
    instead of relying on manually running data/scripts/*.sh + the
    hardcoded link_cloud_native_assets.py after each upload. Raster has
    no equivalent auto-mirror yet (see docs/step6-catalog-bridge.md).
    """
    if not created:
        return

    _stamp_creation_metadata(instance)

    if instance.subtype == "vector":
        from uploads_api.tasks import mirror_dataset_to_geoparquet

        mirror_dataset_to_geoparquet.delay(instance.id)


def _stamp_creation_metadata(instance):
    from geonode.base.models import ExtraMetadata
    from geonode.base.utils import validate_extra_metadata
    from geonode.layers.models import Dataset

    try:
        # queryset .update(), not instance.save(), to avoid recursively
        # re-triggering GeoNode's own post_save stack (permissions sync,
        # catalogue reindex) for this same instance.
        Dataset.objects.filter(pk=instance.pk).update(date_type="creation")

        payload = [
            {
                "filter_header": "Dates",
                "field_name": "data_last_updated",
                "field_label": "Data last updated",
                "field_value": instance.date.isoformat(),
            }
        ]
        validated = validate_extra_metadata(payload, instance)
        extra = ExtraMetadata.objects.create(resource=instance.resourcebase_ptr, metadata=validated[0])
        instance.resourcebase_ptr.metadata.add(extra)
    except Exception:
        logger.exception("Failed to stamp creation metadata for dataset %s", instance.id)
