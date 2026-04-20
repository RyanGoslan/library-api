import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify


DEFAULT_DB_CONFIG = {
    "host": "localhost",
    "database": "library_db",
    "user": "postgres",
    "password": "secret",
    "port": "5432"
}

def get_db_connection(db_config):
    conn = psycopg2.connect(**db_config)
    conn.set_client_encoding('UTF8')
    return conn

def init_db(db_config):
    conn = get_db_connection(db_config)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS authors (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    birth_year INT
                );
                CREATE TABLE IF NOT EXISTS books (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    genre VARCHAR(100),
                    year_published INT,
                    author_id INT REFERENCES authors(id) ON DELETE SET NULL,
                    created_by VARCHAR(255) NOT NULL
                );
            """)
            conn.commit()
    finally:
        conn.close()

def create_app(db_config=None):
    """Фабрика застосунків — створює Flask app із заданою конфігурацією БД"""
    app = Flask(__name__)
    app.json.ensure_ascii = False  
    
    if db_config is None:
        db_config = DEFAULT_DB_CONFIG
        
    app.config["DB_CONFIG"] = db_config
    init_db(db_config)

    @app.route('/api/authors', methods=['GET', 'POST'])
    def handle_authors():
        conn = get_db_connection(app.config["DB_CONFIG"])
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            if request.method == 'POST':
                data = request.get_json()
                if not data or 'name' not in data or not data['name'].strip():
                    return jsonify({"error": "field 'name' is required"}), 400
                cur.execute("INSERT INTO authors (name, birth_year) VALUES (%s, %s) RETURNING *",
                            (data['name'], data.get('birth_year')))
                new_author = cur.fetchone()
                conn.commit()
                return jsonify(new_author), 201
            else:
                cur.execute("SELECT * FROM authors ORDER BY id")
                return jsonify(cur.fetchall()), 200
        finally:
            conn.close()

    @app.route('/api/authors/<int:author_id>', methods=['GET', 'DELETE'])
    def handle_author(author_id):
        conn = get_db_connection(app.config["DB_CONFIG"])
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            if request.method == 'GET':
                cur.execute("SELECT * FROM authors WHERE id = %s", (author_id,))
                author = cur.fetchone()
                if not author: return jsonify({"error": "Author not found"}), 404
                return jsonify(author), 200
            else:
                cur.execute("DELETE FROM authors WHERE id = %s RETURNING id", (author_id,))
                res = cur.fetchone()
                conn.commit()
                if not res: return jsonify({"error": "Author not found"}), 404
                return '', 204
        finally:
            conn.close()

    @app.route('/api/books', methods=['GET', 'POST'])
    def handle_books():
        conn = get_db_connection(app.config["DB_CONFIG"])
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            if request.method == 'POST':
                data = request.get_json()
                if not data or 'title' not in data or not data.get('title').strip():
                    return jsonify({"error": "field 'title' is required"}), 400
                if 'created_by' not in data or not data.get('created_by').strip():
                    return jsonify({"error": "field 'created_by' is required"}), 400
                
                if data.get('author_id'):
                    cur.execute("SELECT id FROM authors WHERE id = %s", (data['author_id'],))
                    if not cur.fetchone():
                        return jsonify({"error": f"Author with id {data['author_id']} not found"}), 400

                cur.execute("""INSERT INTO books (title, genre, year_published, author_id, created_by) 
                               VALUES (%s, %s, %s, %s, %s) RETURNING *""",
                            (data['title'], data.get('genre'), data.get('year_published'), 
                             data.get('author_id'), data['created_by']))
                new_book = cur.fetchone()
                conn.commit()
                return jsonify(new_book), 201
            else:
                genre = request.args.get('genre')
                q = request.args.get('q')
                author_id = request.args.get('author_id')
                query = "SELECT * FROM books WHERE 1=1"
                params = []
                if genre: query += " AND genre = %s"; params.append(genre)
                if q: query += " AND title ILIKE %s"; params.append(f'%{q}%')
                if author_id: query += " AND author_id = %s"; params.append(author_id)
                cur.execute(query + " ORDER BY id", tuple(params))
                return jsonify(cur.fetchall()), 200
        finally:
            conn.close()

    @app.route('/api/books/<int:book_id>', methods=['GET', 'PUT', 'DELETE'])
    def handle_single_book(book_id):
        conn = get_db_connection(app.config["DB_CONFIG"])
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            if request.method == 'GET':
                cur.execute("SELECT * FROM books WHERE id = %s", (book_id,))
                book = cur.fetchone()
                if not book: return jsonify({"error": "Book not found"}), 404
                return jsonify(book), 200
            elif request.method == 'PUT':
                data = request.get_json()
                cur.execute("""UPDATE books SET 
                               title = COALESCE(%s, title), 
                               genre = COALESCE(%s, genre), 
                               year_published = COALESCE(%s, year_published),
                               author_id = COALESCE(%s, author_id)
                               WHERE id = %s RETURNING *""",
                            (data.get('title'), data.get('genre'), data.get('year_published'), 
                             data.get('author_id'), book_id))
                updated = cur.fetchone()
                conn.commit()
                if not updated: return jsonify({"error": "Book not found"}), 404
                return jsonify(updated), 200
            else:
                cur.execute("DELETE FROM books WHERE id = %s RETURNING id", (book_id,))
                res = cur.fetchone()
                conn.commit()
                if not res: return jsonify({"error": "Book not found"}), 404
                return '', 204
        finally:
            conn.close()

    @app.route('/api/authors/<int:author_id>/books', methods=['GET'])
    def get_author_books_route(author_id):
        conn = get_db_connection(app.config["DB_CONFIG"])
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT id FROM authors WHERE id = %s", (author_id,))
            if not cur.fetchone(): return jsonify({"error": "Author not found"}), 404
            cur.execute("SELECT * FROM books WHERE author_id = %s", (author_id,))
            return jsonify(cur.fetchall()), 200
        finally:
            conn.close()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)