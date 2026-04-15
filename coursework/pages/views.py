from django.contrib.auth.models import User
from django.db.models import Avg, Count
from rest_framework import generics, permissions, status, viewsets, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import SAFE_METHODS

from .models import Author, Category, Book, Review
from .serializers import (
    AuthorSerializer,
    CategorySerializer,
    BookSerializer,
    BookListSerializer,
    BookDetailSerializer,
    ReviewSerializer,
    RegisterSerializer,
    UserProfileSerializer,
    RecommendationBookSerializer,
)


# -----------------------------
# Permission Classes
# -----------------------------
class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Read-only for everyone.
    Write permissions only for admin users.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Allow read-only access for everyone.
    Only the owner can update/delete the object.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and obj.user == request.user


# -----------------------------
# Helper Function
# -----------------------------
def update_book_rating(book):
    """
    Recalculate and update a book's average rating and total review count.
    """
    stats = book.reviews.aggregate(
        avg_rating=Avg('rating'),
        review_count=Count('id')
    )

    book.average_rating = stats['avg_rating'] or 0
    book.total_reviews = stats['review_count'] or 0
    book.save(update_fields=['average_rating', 'total_reviews'])


# -----------------------------
# Authentication Views
# -----------------------------
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


# -----------------------------
# Author Views
# -----------------------------
class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'nationality']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


# -----------------------------
# Category Views
# -----------------------------
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


# -----------------------------
# Book Views
# -----------------------------
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.select_related('author', 'category').all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'isbn', 'author__name', 'category__name']
    ordering_fields = [
        'title',
        'publication_year',
        'average_rating',
        'total_reviews',
        'created_at'
    ]
    ordering = ['title']

    def get_serializer_class(self):
        if self.action == 'list':
            return BookListSerializer
        if self.action in ['retrieve', 'create', 'update', 'partial_update']:
            return BookDetailSerializer
        return BookSerializer

    def get_queryset(self):
        queryset = Book.objects.select_related('author', 'category').all()

        category_id = self.request.query_params.get('category')
        author_id = self.request.query_params.get('author')
        publication_year = self.request.query_params.get('publication_year')
        language = self.request.query_params.get('language')

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        if author_id:
            queryset = queryset.filter(author_id=author_id)

        if publication_year:
            queryset = queryset.filter(publication_year=publication_year)

        if language:
            queryset = queryset.filter(language__iexact=language)

        return queryset


# -----------------------------
# Review Views
# -----------------------------
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related('user', 'book').all()
    serializer_class = ReviewSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        elif self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        queryset = Review.objects.select_related('user', 'book').all()

        book_id = self.request.query_params.get('book')
        user_id = self.request.query_params.get('user')
        rating = self.request.query_params.get('rating')

        if book_id:
            queryset = queryset.filter(book_id=book_id)

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        if rating:
            queryset = queryset.filter(rating=rating)

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        book = instance.book
        instance.delete()
        update_book_rating(book)


# -----------------------------
# Recommendation Views
# -----------------------------
class PopularRecommendationView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        books = Book.objects.select_related('author', 'category').all().order_by(
            '-average_rating',
            '-total_reviews',
            'title'
        )[:10]

        serializer = RecommendationBookSerializer(books, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SimilarBooksRecommendationView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, book_id):
        try:
            target_book = Book.objects.select_related('category').get(id=book_id)
        except Book.DoesNotExist:
            return Response(
                {"detail": "Book not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not target_book.category:
            return Response([], status=status.HTTP_200_OK)

        similar_books = Book.objects.select_related('author', 'category').filter(
            category=target_book.category
        ).exclude(
            id=target_book.id
        ).order_by(
            '-average_rating',
            '-total_reviews',
            'title'
        )[:10]

        serializer = RecommendationBookSerializer(similar_books, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserRecommendationView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Find the user's preferred category based on highest-rated reviews
        reviewed_books = Review.objects.filter(user=user).select_related('book__category')

        if not reviewed_books.exists():
            return Response([], status=status.HTTP_200_OK)

        # Count category preference weighted simply by reviews with rating >= 4
        preferred_categories = (
            reviewed_books.filter(rating__gte=4, book__category__isnull=False)
            .values('book__category')
            .annotate(category_count=Count('book__category'))
            .order_by('-category_count')
        )

        if not preferred_categories.exists():
            return Response([], status=status.HTTP_200_OK)

        preferred_category_id = preferred_categories[0]['book__category']

        reviewed_book_ids = reviewed_books.values_list('book_id', flat=True)

        recommended_books = Book.objects.select_related('author', 'category').filter(
            category_id=preferred_category_id
        ).exclude(
            id__in=reviewed_book_ids
        ).order_by(
            '-average_rating',
            '-total_reviews',
            'title'
        )[:10]

        serializer = RecommendationBookSerializer(recommended_books, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)