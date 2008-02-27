-- Copyright (c) 2008 Participatory Culture Foundation
-- See LICENSE for details

CREATE TABLE cg_task_time (
  name VARCHAR(255) NOT NULL PRIMARY KEY,
  last_run_time DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
