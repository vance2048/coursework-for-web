# Coursework for Web - Book Recommendation API

A Django REST Framework backend project for book recommendations, including user authentication, resource management, reviews, and recommendation endpoints.

## Features

- Authentication: register, JWT login, token refresh, token verify, profile endpoint
- Resource APIs: authors, categories, books, and reviews
- Permission rules:
  - Read operations are public by default
  - Write operations for authors/categories/books are admin-only
  - Review creation requires login; update/delete is owner-only
- Recommendation APIs:
  - Popular books (by rating and review count)
  - Similar books (by category)
  - User preference recommendations (based on high-rated reviews)
- Management commands:
  - `seed` for demo data (idempotent)
  - `clear` for business data cleanup (keeps superusers)

## Tech Stack

- Python 3
- Django 3.2.25
- Django REST Framework==3.14.0
- djangorestframework-simplejwt==5.2.2
- SQLite3

## Project Structure

```text
coursework-for-web/
├─ README.md
└─ coursework/
   ├─ manage.py
   ├─ db.sqlite3
   ├─ coursework/
   │  ├─ settings.py
   │  ├─ urls.py
   │  ├─ asgi.py
   │  └─ wsgi.py
   └─ pages/
      ├─ models.py
      ├─ serializers.py
      ├─ views.py
      ├─ urls.py
      ├─ management/
      │  └─ commands/
      │     ├─ seed.py
      │     └─ clear.py
      └─ migrations/
```

## Quick Start

### 1. Enter the project directory

```bash
cd coursework
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
```

Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

Windows CMD:

```bash
.venv\Scripts\activate.bat
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

This repository currently does not include `requirements.txt`, so install core dependencies manually:

```bash
pip install django==3.2.25 djangorestframework==3.14.0 djangorestframework-simplejwt==5.2.2
```

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Create a superuser (recommended)

```bash
python manage.py createsuperuser
```

### 6. Start the server

```bash
python manage.py runserver
```

Default URL: `http://127.0.0.1:8000/`

## Preloaded Database Data

- This repository includes preloaded data in `coursework/db.sqlite3`.
- If you want to regenerate default data, run `clear` first, then run `seed`.
- You must create your own superuser before using admin-only endpoints and admin site access.

Recommended reset flow:

```bash
cd coursework
python manage.py createsuperuser
python manage.py clear --yes
python manage.py seed
```

## API Base URL

- Base URL: `http://127.0.0.1:8000/api/`

## API Interface Document

- For full API interface details, see the PDF file: [API Interface Information Table.pdf](./API_Interface_Information_Table.pdf)

## Authorization Reminder

- Some operations (especially `DELETE`, and other write actions on authors/categories/books) require superuser/admin permissions.
- For protected endpoints, add the JWT access token in the request header before sending requests:

```http
Authorization: Bearer <access_token>
```

- For registration and login endpoints (`POST /api/auth/register/`, `POST /api/auth/login/`), remove the `Authorization` header and call them without token auth.

## Authentication Endpoints

- `POST /api/auth/register/`: Register a user
- `POST /api/auth/login/`: Get `access` and `refresh` tokens
- `POST /api/auth/refresh/`: Refresh `access` token
- `POST /api/auth/verify/`: Verify token
- `GET /api/auth/me/`: Get current user profile (authenticated)

Notes:

- For `POST /api/auth/login/` and `POST /api/auth/register/`, make sure the request header does **not** include `Authorization`.
- For `POST /api/auth/refresh/` and `POST /api/auth/verify/`, include the corresponding JWT token in the request body.
- For `GET /api/auth/me/`, include `Authorization: Bearer <access_token>` in the request header.

Body examples:

```json
// Refresh
{
  "refresh": "<refresh_token>"
}
```

```json
// Verify
{
  "token": "<access_or_refresh_token>"
}
```

## Resource Endpoints

### Authors

- `GET /api/authors/`
- `POST /api/authors/` (admin only)
- `GET /api/authors/{id}/`
- `PUT/PATCH/DELETE /api/authors/{id}/` (admin only)

### Categories

- `GET /api/categories/`
- `POST /api/categories/` (admin only)
- `GET /api/categories/{id}/`
- `PUT/PATCH/DELETE /api/categories/{id}/` (admin only)

### Books

- `GET /api/books/`
- `POST /api/books/` (admin only)
- `GET /api/books/{id}/`
- `PUT/PATCH/DELETE /api/books/{id}/` (admin only)

List query parameters:

- `category=<category_id>`
- `author=<author_id>`
- `publication_year=<year>`
- `language=<language>`
- `search=<keyword>`
- `ordering=title|-average_rating|publication_year`

### Reviews

- `GET /api/reviews/`
- `POST /api/reviews/` (authenticated)
- `GET /api/reviews/{id}/`
- `PUT/PATCH/DELETE /api/reviews/{id}/` (owner only)

List query parameters:

- `book=<book_id>`
- `user=<user_id>`
- `rating=<1-5>`

## Recommendation Endpoints

- `GET /api/recommendations/popular/`
  - Top 10 popular books sorted by rating and review count
- `GET /api/recommendations/similar/{book_id}/`
  - Books in the same category as target book (excluding itself)
- `GET /api/recommendations/user/{user_id}/`
  - Recommends books based on the user's high-rated reviews (`rating >= 4`)

## Management Commands

### Seed Demo Data

```bash
python manage.py seed
```

Insert only authors, categories, and books (no users/reviews):

```bash
python manage.py seed --skip-reviews
```

Default demo users (when first created):

- `seed_reader_1` / `seedpass123`
- `seed_reader_2` / `seedpass123`

### Clear Business Data

Delete all reviews, books, authors, categories, and non-superuser accounts:

```bash
python manage.py clear
```

Skip confirmation:

```bash
python manage.py clear --yes
```

Keep session rows:

```bash
python manage.py clear --yes --keep-sessions
```

Note: if no superuser exists, `clear` will refuse to run to prevent lockout.

## Permission Summary

- `AllowAny`: most read endpoints are publicly accessible
- `IsAdminOrReadOnly`: admin-only writes for authors/categories/books
- `IsOwnerOrReadOnly`: only review owner can update/delete

## Testing

`pages/tests.py` is currently a placeholder. Suggested additions:

- Authentication flow tests
- Permission and authorization tests
- Review uniqueness constraint tests (one review per user per book)
- Recommendation endpoint behavior tests

## Future Improvements

- Add and maintain `requirements.txt` with pinned versions
- Add Swagger / ReDoc API documentation
- Improve automated tests and CI integration
- Add pagination, throttling, and caching
- Improve recommendation algorithm (collaborative/content-based methods)


## GitHub repository

https://github.com/vance2048/coursework-for-web

