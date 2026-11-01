"""Run once: uv run python scripts_create_admin.py admin@example.com 'StrongPass123' """
import sys

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
import app.models  # noqa: F401
from app.models.enums import UserRole
from app.models.user import User

Base.metadata.create_all(engine)
email, password = sys.argv[1], sys.argv[2]
with SessionLocal() as db:
    db.add(User(email=email.lower(), full_name="Admin", role=UserRole.admin, hashed_password=hash_password(password)))
    db.commit()
print("Admin created")
