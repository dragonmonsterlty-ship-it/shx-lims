from __future__ import annotations

import argparse
from pathlib import Path
import sys


sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.users import get_user_by_username  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update a development admin user.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--email")
    parser.add_argument("--department")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = SessionLocal()
    try:
        user = get_user_by_username(db, args.username)
        if user is None:
            user = User(
                username=args.username,
                full_name=args.full_name,
                email=args.email,
                password_hash=hash_password(args.password),
                role="admin",
                department=args.department,
                is_active=True,
                must_change_password=False,
            )
            db.add(user)
            action = "created"
        else:
            user.full_name = args.full_name
            user.email = args.email
            user.password_hash = hash_password(args.password)
            user.role = "admin"
            user.department = args.department
            user.is_active = True
            user.must_change_password = False
            action = "updated"
        db.commit()
        print(f"Admin user {action}: {args.username}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
