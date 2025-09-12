"""Simple test to verify DB connectivity using SQLAlchemy engine with diagnostics."""

from app.models.database import engine
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


def test_db_connection() -> dict:
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            value = result.scalar()
            return {
                "ok": value == 1,
                "driver": engine.url.get_driver_name(),
                "url": str(engine.url).replace(engine.url.password or "", "*****") if engine.url.password else str(engine.url)
            }
    except SQLAlchemyError as e:
        return {
            "ok": False,
            "driver": engine.url.get_driver_name(),
            "url": str(engine.url).replace(engine.url.password or "", "*****") if engine.url.password else str(engine.url),
            "error": str(e.__cause__ or e)
        }
    except Exception as e:
        return {
            "ok": False,
            "driver": engine.url.get_driver_name(),
            "url": str(engine.url).replace(engine.url.password or "", "*****") if engine.url.password else str(engine.url),
            "error": str(e)
        }


if __name__ == "__main__":
    res = test_db_connection()
    if res.get("ok"):
        print("✅ Database connection successful")
    else:
        print("❌ Database connection failed")
    print(f"driver: {res.get('driver')}")
    print(f"url: {res.get('url')}")
    if not res.get("ok"):
        err = res.get("error", "")
        if err:
            print(f"error: {err}")
        try:
            import pyodbc
            drivers = pyodbc.drivers()
            if drivers:
                print("Installed ODBC drivers:")
                for d in drivers:
                    print(f" - {d}")
        except Exception:
            pass


