"""Admin command line.

python -m app.admin set-role you@example.com admin      # user | pro | moderator | admin
python -m app.admin set-status someone@example.com active   # probation | active | suspended | banned
"""

import argparse
import sys

from sqlalchemy import func, select

from app.db import SessionLocal
from app.modules.accounts.models import Role, User, UserStatus


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m app.admin")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("set-role")
    r.add_argument("email")
    r.add_argument("role", choices=[x.value for x in Role])
    s = sub.add_parser("set-status")
    s.add_argument("email")
    s.add_argument("status", choices=[x.value for x in UserStatus])
    args = p.parse_args(argv)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(func.lower(User.email) == args.email.lower()))
        if user is None:
            print(f"No user with email {args.email}", file=sys.stderr)
            return 1
        if args.cmd == "set-role":
            user.role = Role(args.role)
            if user.has_role(Role.pro):
                user.status = UserStatus.active
        else:
            user.status = UserStatus(args.status)
        db.commit()
        print(f"{user.email}: role={user.role.value} status={user.status.value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
