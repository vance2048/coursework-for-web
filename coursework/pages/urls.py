from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import (
    RegisterView,
    ProfileView,
    AuthorViewSet,
    CategoryViewSet,
    BookViewSet,
    ReviewViewSet,
    PopularRecommendationView,
    SimilarBooksRecommendationView,
    UserRecommendationView,
)

router = DefaultRouter()
router.register(r'authors', AuthorViewSet, basename='author')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'books', BookViewSet, basename='book')
router.register(r'reviews', ReviewViewSet, basename='review')

urlpatterns = [
    path('', include(router.urls)),

    # Auth
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('auth/me/', ProfileView.as_view(), name='profile'),

    # Recommendations
    path('recommendations/popular/', PopularRecommendationView.as_view(), name='popular-recommendations'),
    path('recommendations/similar/<int:book_id>/', SimilarBooksRecommendationView.as_view(), name='similar-recommendations'),
    path('recommendations/user/<int:user_id>/', UserRecommendationView.as_view(), name='user-recommendations'),
]