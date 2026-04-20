import os
import pytest
import psycopg2
from app import create_app

TEST_DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    "database": os.environ.get("POSTGRES_DB", "library_test_db"),
    "user": os.environ.get("POSTGRES_USER", "postgres"),
    "password": os.environ.get("POSTGRES_PASSWORD", "secret"),
}

@pytest.fixture(scope="session")
def test_db():
    conn = psycopg2.connect(
        host=TEST_DB_CONFIG["host"],
        port=TEST_DB_CONFIG["port"],
        user=TEST_DB_CONFIG["user"],
        password=TEST_DB_CONFIG["password"],
        database="postgres",
    )
    conn.autocommit = True
    db_name = TEST_DB_CONFIG["database"]
    
    with conn.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS {db_name}")
        cur.execute(f"CREATE DATABASE {db_name}")
    conn.close()
    
    yield TEST_DB_CONFIG
    

    conn = psycopg2.connect(
        host=TEST_DB_CONFIG["host"],
        port=TEST_DB_CONFIG["port"],
        user=TEST_DB_CONFIG["user"],
        password=TEST_DB_CONFIG["password"],
        database="postgres",
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS {db_name}")
    conn.close()

@pytest.fixture(scope="session")
def app(test_db):
    app = create_app(db_config=test_db)
    app.config["TESTING"] = True
    return app

@pytest.fixture
def client(app):
    conn = psycopg2.connect(**app.config["DB_CONFIG"])
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE books, authors RESTART IDENTITY CASCADE;")
            conn.commit()
    finally:
        conn.close()
        
    with app.test_client() as client:
        yield client