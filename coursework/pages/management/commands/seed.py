from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Avg, Count

from pages.models import Author, Book, Category, Review


def refresh_book_stats(book):
    stats = book.reviews.aggregate(
        avg_rating=Avg("rating"),
        review_count=Count("id"),
    )
    book.average_rating = stats["avg_rating"] or Decimal("0.00")
    book.total_reviews = stats["review_count"] or 0
    book.save(update_fields=["average_rating", "total_reviews"])


class Command(BaseCommand):
    help = "Insert demo authors, categories, books, users, and reviews (safe to run multiple times)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-reviews",
            action="store_true",
            help="Only seed authors, categories, and books (no users or reviews).",
        )

    def handle(self, *args, **options):
        skip_reviews = options["skip_reviews"]

        categories_data = [
            ("Fiction", "Novels and stories."),
            ("Science", "Popular science and textbooks."),
            ("History", "Historical works."),
        ]
        categories = {}
        for name, desc in categories_data:
            obj, created = Category.objects.get_or_create(
                name=name, defaults={"description": desc}
            )
            categories[name] = obj
            self._line("Category", name, created)

        authors_data = [
            ("Liu Cixin", "Chinese science fiction writer.", "China"),
            ("George Orwell", "English novelist and essayist.", "United Kingdom"),
            ("Yuval Noah Harari", "Historian and author.", "Israel"),
        ]
        authors = {}
        for name, bio, nation in authors_data:
            obj, created = Author.objects.get_or_create(
                name=name,
                defaults={"biography": bio, "nationality": nation},
            )
            authors[name] = obj
            self._line("Author", name, created)

        books_data = [
            {
                "title": "The Three-Body Problem",
                "isbn": "978-0765377067",
                "author": "Liu Cixin",
                "category": "Science",
                "year": 2014,
                "pages": 400,
                "language": "English",
                "description": "First novel in the Remembrance of Earth's Past trilogy.",
            },
            {
                "title": "1984",
                "isbn": "978-0451524935",
                "author": "George Orwell",
                "category": "Fiction",
                "year": 1950,
                "pages": 328,
                "language": "English",
                "description": "Dystopian social science fiction.",
            },
            {
                "title": "Sapiens: A Brief History of Humankind",
                "isbn": "978-0062316097",
                "author": "Yuval Noah Harari",
                "category": "History",
                "year": 2015,
                "pages": 464,
                "language": "English",
                "description": "Survey of human history from Stone Age to modernity.",
            },
            {
                "title": "The Dark Forest",
                "isbn": "978-0765377081",
                "author": "Liu Cixin",
                "category": "Science",
                "year": 2015,
                "pages": 512,
                "language": "English",
                "description": "Second book in the Remembrance of Earth's Past trilogy.",
            },
            {
                "title": "Ball Lightning",
                "isbn": "978-0765379471",
                "author": "Liu Cixin",
                "category": "Science",
                "year": 2018,
                "pages": 384,
                "language": "English",
                "description": "Standalone SF novel.",
            },
            {
                "title": "Animal Farm",
                "isbn": "978-0451526342",
                "author": "George Orwell",
                "category": "Fiction",
                "year": 1996,
                "pages": 140,
                "language": "English",
                "description": "Allegorical novella.",
            },
        ]

        books = []
        for row in books_data:
            author = authors[row["author"]]
            category = categories[row["category"]]
            book, created = Book.objects.get_or_create(
                isbn=row["isbn"],
                defaults={
                    "title": row["title"],
                    "author": author,
                    "category": category,
                    "publication_year": row["year"],
                    "pages": row["pages"],
                    "language": row["language"],
                    "description": row["description"],
                },
            )
            books.append(book)
            self._line("Book", book.title, created)

        if skip_reviews:
            self.stdout.write(self.style.SUCCESS("Done (reviews skipped)."))
            return

        demo_users = [
            ("seed_reader_1", "reader1@example.com"),
            ("seed_reader_2", "reader2@example.com"),
        ]
        users = []
        for username, email in demo_users:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email},
            )
            if created:
                user.set_password("seedpass123")
                user.save(update_fields=["password"])
            users.append(user)
            self._line("User", username, created)

        # UserRecommendationView: rating>=4 + category + unreviewed book in that category.
        review_specs = [
            (users[0], books[0], 5, "Excellent hard SF."),
            (users[0], books[2], 3, "Interesting but not a top pick."),
            (users[1], books[1], 5, "Still very relevant."),
            (users[1], books[2], 3, "Dense in places."),
        ]

        touched_books = set()
        for user, book, rating, comment in review_specs:
            _review, created = Review.objects.get_or_create(
                user=user,
                book=book,
                defaults={"rating": rating, "comment": comment},
            )
            self._line("Review", f"{user.username} → {book.title}", created)
            touched_books.add(book)

        for book in touched_books:
            refresh_book_stats(book)

        self.stdout.write(self.style.SUCCESS("Done."))
        self.stdout.write(
            "Demo logins (if users were just created): seed_reader_1 / seed_reader_2 — password: seedpass123"
        )
        u0, u1 = users[0], users[1]
        self.stdout.write(
            f"User recommendations: GET /api/recommendations/user/{u0.pk}/ "
            f"(Science) and /api/recommendations/user/{u1.pk}/ (Fiction)."
        )

    def _line(self, kind, name, created):
        status = "created" if created else "exists"
        self.stdout.write(f"  [{kind}] {name} — {status}")