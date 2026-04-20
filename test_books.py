class TestBooks:
    def test_get_books_empty(self, client):
        response = client.get("/api/books")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_create_book(self, client):
        response = client.post("/api/books", json={
            "title": "Тіні забутих предків",
            "genre": "Повість",
            "year_published": 1911,
            "created_by": "Martyniuk Stanislav"
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "Тіні забутих предків"
        assert data["created_by"] == "Martyniuk Stanislav"

    def test_create_book_without_title(self, client):
        response = client.post("/api/books", json={"created_by": "Martyniuk Stanislav"})
        assert response.status_code == 400

    def test_create_book_without_created_by(self, client):
        response = client.post("/api/books", json={"title": "Книга"})
        assert response.status_code == 400

    def test_create_book_with_author(self, client):
        author = client.post("/api/authors", json={"name": "Михайло Коцюбинський"}).get_json()
        response = client.post("/api/books", json={
            "title": "Fata Morgana",
            "author_id": author["id"],
            "created_by": "Martyniuk Stanislav"
        })
        assert response.status_code == 201
        assert response.get_json()["author_id"] == author["id"]

    def test_create_book_with_nonexistent_author(self, client):
        response = client.post("/api/books", json={
            "title": "Книга",
            "author_id": 999,
            "created_by": "Martyniuk Stanislav"
        })
        assert response.status_code == 400

    def test_get_book_by_id(self, client):
        book = client.post("/api/books", json={
            "title": "Книга",
            "created_by": "Martyniuk Stanislav"
        }).get_json()
        response = client.get(f"/api/books/{book['id']}")
        assert response.status_code == 200

    def test_get_book_not_found(self, client):
        response = client.get("/api/books/999")
        assert response.status_code == 404

    def test_delete_book(self, client):
        book = client.post("/api/books", json={
            "title": "Книга для видалення",
            "created_by": "Martyniuk Stanislav"
        }).get_json()
        
        response = client.delete(f"/api/books/{book['id']}")
        assert response.status_code == 204
        

        response_get = client.get(f"/api/books/{book['id']}")
        assert response_get.status_code == 404


class TestBooksFilter:
    def test_filter_by_genre(self, client):
        client.post("/api/books", json={"title": "Кобзар", "genre": "poetry", "created_by": "Martyniuk Stanislav"})
        client.post("/api/books", json={"title": "Тигролови", "genre": "novel", "created_by": "Martyniuk Stanislav"})
        
        response = client.get("/api/books?genre=poetry")
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["title"] == "Кобзар"

    def test_filter_by_author_id(self, client):
        author1 = client.post("/api/authors", json={"name": "Автор 1"}).get_json()
        author2 = client.post("/api/authors", json={"name": "Автор 2"}).get_json()
        
        client.post("/api/books", json={"title": "Книга 1", "author_id": author1["id"], "created_by": "Martyniuk Stanislav"})
        client.post("/api/books", json={"title": "Книга 2", "author_id": author2["id"], "created_by": "Martyniuk Stanislav"})
        
        response = client.get(f"/api/books?author_id={author1['id']}")
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["title"] == "Книга 1"

    def test_search_by_title(self, client):
        client.post("/api/books", json={"title": "Кобзар", "created_by": "Martyniuk Stanislav"})
        client.post("/api/books", json={"title": "Тигролови", "created_by": "Martyniuk Stanislav"})
        
        response = client.get("/api/books?q=обз")
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["title"] == "Кобзар"

    def test_filter_no_results(self, client):
        client.post("/api/books", json={"title": "Кобзар", "genre": "poetry", "created_by": "Martyniuk Stanislav"})
        response = client.get("/api/books?genre=scifi")
        assert response.status_code == 200
        assert response.get_json() == []