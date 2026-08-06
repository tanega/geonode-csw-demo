from django.apps import AppConfig


class UploadsApiConfig(AppConfig):
    name = "uploads_api"

    def ready(self):
        from django.db.models.signals import post_save
        from geonode.layers.models import Dataset

        from uploads_api.signals import on_dataset_saved

        post_save.connect(
            on_dataset_saved, sender=Dataset, dispatch_uid="uploads_api_on_dataset_saved"
        )
