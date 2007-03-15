-- Make tables to store FULLTEXT indexes.  Unfortunately, this means they must
-- be MyISAM tables
CREATE TABLE cg_channel_search_data (
  channel_id INT(11) NOT NULL PRIMARY KEY,
  important_text VARCHAR(255) NOT NULL,
  text TEXT NOT NULL,
  FULLTEXT INDEX important_text_index (important_text),
  FULLTEXT INDEX text_index (important_text, text)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
CREATE TABLE cg_item_search_data (
  item_id INT(11) NOT NULL PRIMARY KEY,
  important_text VARCHAR(255) NOT NULL,
  text TEXT NOT NULL,
  FULLTEXT INDEX important_text_index (important_text),
  FULLTEXT INDEX text_index (important_text, text)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
-- FULLTEXT indexses only work on MyISAM tables
