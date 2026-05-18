from backend.db.database import get_database_url, init_db


def main() -> None:
    database_url = get_database_url()
    if not database_url:
        raise SystemExit("DATABASE_URL is not set. Create .env first.")

    created = init_db()
    if not created:
        raise SystemExit("Database initialization failed. Check that PostgreSQL is running.")

    print("Database tables are ready.")


if __name__ == "__main__":
    main()
