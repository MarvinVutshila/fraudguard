#!/usr/bin/env python
"""
Create an admin user for FraudGuard.
Run: python scripts/create_admin.py --username admin@fraudguard.com --password your-password
"""

import argparse
import os
import sys
import logging
from getpass import getpass
from passlib.context import CryptContext
from fraud_detection.core.config import DB_DSN
from fraud_detection.database.postgres_db import Database, init_db_pool, create_tables

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Password hashing (same as auth.py)
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")


def create_admin_user(username: str, password: str, role: str = "admin", status: str = "active"):
    """
    Create or update a user with admin privileges.
    """
    if not username or not password:
        raise ValueError("Username and password are required.")

    # Connect to the database
    init_db_pool(DB_DSN, min_conn=1, max_conn=10)
    create_tables()
    db = Database()

    # Hash the password
    hashed = pwd_context.hash(password)

    # Check if user already exists
    existing = db.get_user_by_username(username)
    if existing:
        # Update existing user to admin/active if needed
        user_id = existing["id"]
        db.update_user_status(user_id, status)
        logger.info(f"✅ Updated user '{username}' (ID: {user_id}) to status='{status}'")
        logger.info(f"ℹ️  If role was not 'admin', update it manually via SQL or rerun with --force.")
        return

    # Insert new user
    user_id = db.create_user(
        username=username,
        password=hashed,
        role=role,
        status=status,
        avatar_url=None,
    )
    logger.info(f"✅ Admin user '{username}' created with ID {user_id}")
    logger.info(f"   Role: {role} | Status: {status}")


def main():
    parser = argparse.ArgumentParser(description="Create an admin user for FraudGuard")
    parser.add_argument("--username", help="Admin username (email)")
    parser.add_argument("--password", help="Admin password (if not provided, will prompt securely)")
    parser.add_argument("--role", default="admin", help="User role (admin/analyst)")
    parser.add_argument("--status", default="active", help="User status (active/pending/rejected)")

    args = parser.parse_args()

    username = args.username
    password = args.password

    # Prompt for missing values
    if not username:
        username = input("Enter admin username (email): ").strip()
    if not password:
        password = getpass("Enter admin password: ")

    if not username or not password:
        logger.error("Username and password are required.")
        sys.exit(1)

    # Ensure DATABASE_URL is set
    if not DB_DSN:
        logger.error("DATABASE_URL not found. Please set it in your environment.")
        sys.exit(1)

    try:
        create_admin_user(username, password, args.role, args.status)
    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
