# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

def version_table_exists(connection):
    rows = connection.execute("SHOW TABLES")
    tables = [row[0] for row in rows]
    return 'cg_db_version' in tables

def initialize_version_table(connection):
    if not version_table_exists(connection):
        connection.execute("""\
CREATE TABLE cg_db_version(version INTEGER NOT NULL) 
ENGINE=InnoDB DEFAULT CHARSET=utf8;
""")
        connection.execute("INSERT INTO cg_db_version VALUES(-1)")

def get_version(connection):
    rows = connection.execute("SELECT version from cg_db_version")
    return rows[0][0]

def set_version(connection, version):
    connection.execute("UPDATE cg_db_version set version=%s", version)
    connection.commit()
