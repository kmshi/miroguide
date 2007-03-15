CREATE TABLE bad_syntax (
	foo integer NOT NULL PRIMARY KEY,
	FOREIGN KEY (foo) REFERENCES non_existant (id)
) ENGINE=InnoDB;
