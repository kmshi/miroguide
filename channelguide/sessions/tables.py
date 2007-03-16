from sqlalchemy import Column, String, DateTime, Table

from channelguide import db

sessions = Table('cg_session', db.metadata,
        Column('session_key', String(40), nullable=False, primary_key=True),
        Column('data', String, nullable=False),
        Column('expires', DateTime, nullable=False))
