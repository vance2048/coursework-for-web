from django.contrib.auth.models import User
from rest_framework import serializers
from django.db.models import Avg, Count

from .models import Author, Category, Book, Review


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined']
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'password',
            'confirm_password',
            'first_name',
            'last_name'
        ]
        read_only_fields = ['id']

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = [
            'id',
            'name',
            'biography',
            'nationality',
            'birth_date',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            'id',
            'name',
            'description',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BookListSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Book
        fields = [
            'id',
            'title',
            'isbn',
            'publication_year',
            'language',
            'pages',
            'author',
            'author_name',
            'category',
            'category_name',
            'average_rating',
            'total_reviews'
        ]
        read_only_fields = ['id', 'average_rating', 'total_reviews']


class BookDetailSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    author_id = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all(),
        source='author',
        write_only=True
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        allow_null=True,
        required=False
    )

    class Meta:
        model = Book
        fields = [
            'id',
            'title',
            'isbn',
            'description',
            'publication_year',
            'language',
            'pages',
            'cover_image_url',
            'author',
            'author_id',
            'category',
            'category_id',
            'average_rating',
            'total_reviews',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'average_rating',
            'total_reviews',
            'created_at',
            'updated_at'
        ]


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = [
            'id',
            'title',
            'isbn',
            'description',
            'publication_year',
            'language',
            'pages',
            'cover_image_url',
            'author',
            'category',
            'average_rating',
            'total_reviews',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'average_rating',
            'total_reviews',
            'created_at',
            'updated_at'
        ]


class ReviewSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    book_title = serializers.CharField(source='book.title', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id',
            'user',
            'user_id',
            'book',
            'book_title',
            'rating',
            'comment',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'user', 'user_id', 'created_at', 'updated_at']

    def validate(self, attrs):
        request = self.context.get('request')
        book = attrs.get('book')

        # 创建评论时检查是否重复评论
        if request and request.method == 'POST':
            if Review.objects.filter(user=request.user, book=book).exists():
                raise serializers.ValidationError({
                    'book': 'You have already reviewed this book.'
                })

        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        # `user` may already be injected by serializer.save(user=...) in the view.
        user = validated_data.pop('user', None) or request.user
        review = Review.objects.create(user=user, **validated_data)
        self.update_book_rating(review.book)
        return review

    def update(self, instance, validated_data):
        review = super().update(instance, validated_data)
        self.update_book_rating(review.book)
        return review

    def update_book_rating(self, book):
        stats = book.reviews.aggregate(
            avg_rating=Avg('rating'),
            review_count=Count('id')
        )

        book.average_rating = stats['avg_rating'] or 0
        book.total_reviews = stats['review_count'] or 0
        book.save(update_fields=['average_rating', 'total_reviews'])


class RecommendationBookSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Book
        fields = [
            'id',
            'title',
            'author_name',
            'category_name',
            'average_rating',
            'total_reviews'
        ]