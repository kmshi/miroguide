-- Copyright (c) 2008 Participatory Culture Foundation
-- See LICENSE for details

ALTER TABLE cg_cobranding CHANGE long_title html_title VARCHAR(100) NOT NULL, CHANGE short_title page_title VARCHAR(100) NOT NULL, ADD icon_url VARCHAR(100) AFTER url;  
