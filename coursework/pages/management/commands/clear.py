from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import transaction

from pages.models import Author, Book, Category, Review


class Command(BaseCommand):
    help = (
        "Delete all app data (reviews, books, authors, categories) and all users "
        "except superusers (is_superuser=True). Optionally clear sessions."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip confirmation prompt (use with care).",
        )
        parser.add_argument(
            "--keep-sessions",
            action="store_true",
            help="Do not delete django_session rows.",
        )

    def handle(self, *args, **options):
        super_count = User.objects.filter(is_superuser=True).count()
        if super_count == 0:
            self.stderr.write(
                self.style.ERROR(
                    "No superuser (is_superuser=True) in the database. "
                    "Refusing to delete users to avoid total lockout. "
                    "Create one with: python manage.py createsuperuser"
                )
            )
            return

        if not options["yes"]:
            self.stdout.write(
                self.style.WARNING(
                    "This will delete: all Reviews, Books, Authors, Categories, "
                    "and every User who is NOT a superuser."
                )
            )
            confirm = input('Type "yes" to continue: ')
            if confirm.strip().lower() != "yes":
                self.stdout.write("Aborted.")
                return

        with transaction.atomic():
            n_rev = Review.objects.all().delete()[0]
            n_book = Book.objects.all().delete()[0]
            n_author = Author.objects.all().delete()[0]
            n_cat = Category.objects.all().delete()[0]

            users_qs = User.objects.filter(is_superuser=False)
            n_users = users_qs.count()
            users_qs.delete()

            n_sessions = 0
            if not options["keep_sessions"]:
                n_sessions = Session.objects.all().delete()[0]

        self.stdout.write(self.style.SUCCESS("Cleared:"))
        self.stdout.write(f"  Reviews: {n_rev}")
        self.stdout.write(f"  Books: {n_book}")
        self.stdout.write(f"  Authors: {n_author}")
        self.stdout.write(f"  Categories: {n_cat}")
        self.stdout.write(f"  Users (non-superuser): {n_users}")
        if not options["keep_sessions"]:
            self.stdout.write(f"  Sessions: {n_sessions}")
        self.stdout.write(f"  Superusers kept: {super_count}")