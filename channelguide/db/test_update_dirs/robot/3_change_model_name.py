import md5

for result in connection.execute("SELECT * from robot").fetchall():
    new_model = md5.new(result['model_name']).hexdigest()
    connection.execute("UPDATE robot SET model_name=%s WHERE serial=%s",
            (new_model, result['serial']))
