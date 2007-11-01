CREATE TABLE foo (
id serial,
name VARCHAR(40) NOT NULL,
PRIMARY KEY (id));

CREATE TABLE foo_extra (
id integer NOT NULL,
extra_info VARCHAR(40) NOT NULL,
PRIMARY KEY (id),
FOREIGN KEY (id) REFERENCES foo (id) ON DELETE CASCADE);

CREATE TABLE types (
id serial,
string VARCHAR(40) NOT NULL,
dateval timestamp NOT NULL,
boolval boolean NOT NULL,
null_ok VARCHAR(20) NULL,
PRIMARY KEY (id));

CREATE TABLE bar (
id serial,
foo_id integer, 
name VARCHAR(40) NOT NULL,
PRIMARY KEY (id),
FOREIGN KEY (foo_id) REFERENCES foo (id) ON DELETE CASCADE);

CREATE TABLE category (
id serial,
name VARCHAR(40) NOT NULL,
PRIMARY KEY (id));

CREATE TABLE category_map (
category_id integer,
foo_id integer,
FOREIGN KEY (category_id) REFERENCES category (id) ON DELETE CASCADE,
FOREIGN KEY (foo_id) REFERENCES foo (id) ON DELETE CASCADE,
PRIMARY KEY (category_id, foo_id));

CREATE TABLE category_map_with_dups (
category_id integer,
foo_id integer,
other_column integer,
FOREIGN KEY (category_id) REFERENCES category (id) ON DELETE CASCADE,
FOREIGN KEY (foo_id) REFERENCES foo (id) ON DELETE CASCADE,
PRIMARY KEY (category_id, foo_id, other_column));
