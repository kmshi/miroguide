import md5

for result in connection.execute("SELECT model_name, serial from robot"):
    new_model = md5.new(result[0]).hexdigest()
    connection.execute("UPDATE robot SET model_name=%s WHERE serial=%s",
            (new_model, result[1]))
