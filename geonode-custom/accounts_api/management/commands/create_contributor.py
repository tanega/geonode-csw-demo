from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

CONTRIBUTOR_GROUP = "contributors"


class Command(BaseCommand):
    help = "Create (or promote an existing) user into the contributors group."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--email", default="")
        parser.add_argument(
            "--password",
            default=None,
            help="Only used when creating a new user; prompted securely if omitted.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]

        try:
            group = Group.objects.get(name=CONTRIBUTOR_GROUP)
        except Group.DoesNotExist:
            raise CommandError(f"Group '{CONTRIBUTOR_GROUP}' does not exist")

        user, created = User.objects.get_or_create(
            username=username, defaults={"email": options["email"]}
        )

        if created:
            password = options["password"]
            if password is None:
                password = getpass("Password: ")
                if password != getpass("Password (again): "):
                    raise CommandError("Passwords did not match")
            user.set_password(password)
            user.save()

        if group in user.groups.all():
            self.stdout.write(
                self.style.WARNING(
                    f"{'Created' if created else 'Existing'} user '{username}' "
                    f"is already in '{CONTRIBUTOR_GROUP}'"
                )
            )
            return

        user.groups.add(group)
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Promoted existing'} user '{username}' "
                f"-> added to '{CONTRIBUTOR_GROUP}'"
            )
        )
