ALTER TABLE user ADD COLUMN language CHAR(5) NOT NULL DEFAULT '';
ALTER TABLE user ADD COLUMN filter_languages TINYINT NOT NULL DEFAULT '0';
CREATE TABLE user_shown_languages (
       user_id INT(11) NOT NULL,
       language_id INT(11) NOT NULL,
       PRIMARY KEY (user_id, language_id),
       CONSTRAINT fk_user_shown_languages_user FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
       CONSTRAINT fk_user_shown_languages_language FOREIGN KEY (language_id) REFERENCES cg_channel_language (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
