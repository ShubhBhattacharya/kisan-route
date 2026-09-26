"""Shared Flask extension instances.

Kept in their own module (instead of inside app.py) so that blueprint
files can `from extensions import db` without causing circular imports.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
