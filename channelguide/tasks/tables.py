from sqlalchemy import Column, String, DateTime, Table

from channelguide import db

task_time = Table('cg_task_time', db.metadata,
        Column('name', String(255), primary_key=True),
        Column('last_run_time', DateTime, nullable=False))
