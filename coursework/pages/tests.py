from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Author, Book, Category, Review


class AuthEndpointTests(APITestCase):
    def test_register_login_refresh_verify_and_profile(self):
        register_payload = {
            "username": "tester1",
            "email": "tester1@example.com",
            "password": "strongpass123",
            "confirm_password": "strongpass123",
            "first_name": "Test",
            "last_name": "User",
        }
        register_url = reverse("register")
        register_res = self.client.post(register_url, register_payload, format="json")
        self.assertEqual(register_res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="tester1").exists())

        login_url = reverse("token_obtain_pair")
        login_res = self.client.post(
            login_url,
            {"username": "tester1", "password": "strongpass123"},
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        access = login_res.data["access"]
        refresh = login_res.data["refresh"]

        verify_url = reverse("token_verify")
        verify_res = self.client.post(verify_url, {"token": access}, format="json")
        self.assertEqual(verify_res.status_code, status.HTTP_200_OK)

        refresh_url = reverse("token_refresh")
        refresh_res = self.client.post(refresh_url, {"refresh": refresh}, format="json")
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_res.data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        profile_url = reverse("profile")
        profile_res = self.client.get(profile_url)
        self.assertEqual(profile_res.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_res.data["username"], "tester1")


class AuthorPermissionTests(APITestCase):
    def setUp(self):
        self.author_list_url = reverse("author-list")
        self.regular_user = User.objects.create_user(
            username="regular_user",
            password="regularpass123",
        )
        self.admin_user = User.objects.create_user(
            username="admin_user",
            password="adminpass123",
            is_staff=True,
            is_superuser=True,
        )

    def _login_get_access_token(self, username, password):
        login_url = reverse("token_obtain_pair")
        res = self.client.post(
            login_url,
            {"username": username, "password": password},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        return res.data["access"]

    def test_non_admin_cannot_create_author(self):
        access = self._login_get_access_token("regular_user", "regularpass123")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        res = self.client.post(self.author_list_url, {"name": "Blocked Author"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_author(self):
        access = self._login_get_access_token("admin_user", "adminpass123")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        res = self.client.post(self.author_list_url, {"name": "Allowed Author"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Author.objects.filter(name="Allowed Author").exists())


class ReviewBehaviorTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="reviewer", password="reviewpass123")
        self.author = Author.objects.create(name="Liu Cixin")
        self.category = Category.objects.create(name="Science", description="Science books")
        self.book = Book.objects.create(
            title="The Three-Body Problem",
            isbn="978-0000000001",
            author=self.author,
            category=self.category,
        )

    def _auth_as_reviewer(self):
        login_url = reverse("token_obtain_pair")
        res = self.client.post(
            login_url,
            {"username": "reviewer", "password": "reviewpass123"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_review_duplicate_is_rejected(self):
        self._auth_as_reviewer()
        review_list_url = reverse("review-list")

        first = self.client.post(
            review_list_url,
            {"book": self.book.id, "rating": 5, "comment": "Excellent"},
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        second = self.client.post(
            review_list_url,
            {"book": self.book.id, "rating": 4, "comment": "Second review"},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("book", second.data)

    def test_book_rating_stats_update_on_review_create(self):
        self._auth_as_reviewer()
        review_list_url = reverse("review-list")

        res = self.client.post(
            review_list_url,
            {"book": self.book.id, "rating": 4, "comment": "Good"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.book.refresh_from_db()
        self.assertEqual(self.book.total_reviews, 1)
        self.assertEqual(float(self.book.average_rating), 4.0)


class RecommendationEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="userpass123")
        self.author = Author.objects.create(name="George Orwell")
        self.fiction = Category.objects.create(name="Fiction")
        self.history = Category.objects.create(name="History")

        self.book_a = Book.objects.create(
            title="1984",
            isbn="978-0000000002",
            author=self.author,
            category=self.fiction,
        )
        self.book_b = Book.objects.create(
            title="Animal Farm",
            isbn="978-0000000003",
            author=self.author,
            category=self.fiction,
        )
        self.book_c = Book.objects.create(
            title="Sapiens",
            isbn="978-0000000004",
            author=self.author,
            category=self.history,
        )

    def test_popular_recommendations_returns_200(self):
        url = reverse("popular-recommendations")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsInstance(res.data, list)

    def test_similar_books_excludes_target_book(self):
        url = reverse("similar-recommendations", kwargs={"book_id": self.book_a.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        returned_ids = [item["id"] for item in res.data]
        self.assertNotIn(self.book_a.id, returned_ids)

    def test_user_recommendations_based_on_high_rating_category(self):
        # Prefer fiction by rating fiction book >= 4.
        Review.objects.create(user=self.user, book=self.book_a, rating=5, comment="Great")

        url = reverse("user-recommendations", kwargs={"user_id": self.user.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Should recommend an unreviewed fiction book, not the reviewed one.
        returned_ids = [item["id"] for item in res.data]
        self.assertIn(self.book_b.id, returned_ids)
        self.assertNotIn(self.book_a.id, returned_ids)
