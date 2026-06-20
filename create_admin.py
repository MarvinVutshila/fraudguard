#!/usr/bin/env python
import os
import sys
from getpass import getpass
from passlib.context import CryptContext
from fraud_detection.core.config import DB_DSN
from fraud_detection.database.postgres_db import Database, init_db_pool, create_tables

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

def create_admin_user(username, password, role="admin", status="active"):
    init_db_pool(DB_DSN, min_conn=1, max_conn=10)
    create_tables()
    db = Database()
    hashed = pwd_context.hash(password)

    existing = db.get_user_by_username(username)
    if existing:
        db.update_user_status(existing['id'], status)
        print(f"✅ Updated user '{username}' to status='{status}'")
        return

    db.create_user(username, hashed, role, status)
    print(f"✅ Admin user '{username}' created (ID: {db.get_user_by_username(username)['id']})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        username = input("Enter admin username (email): ").strip()
    else:
        username = sys.argv[1]
    password = getpass("Enter admin password: ")
    create_admin_user(username, password)