def initialize_version_table(connection):
    if not connection.engine.has_table('cg_db_version'):
        connection.execute("""\
CREATE TABLE cg_db_version(version INTEGER NOT NULL) 
ENGINE=InnoDB DEFAULT CHARSET=utf8;
""")
        connection.execute("insert into cg_db_version values(-1)")

def get_version(connection):
    results = connection.execute("SELECT version from cg_db_version")
    return results.fetchone()['version']

def set_version(connection, version):
    connection.execute("UPDATE cg_db_version set version=%s", version)
