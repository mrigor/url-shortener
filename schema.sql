drop table if exists urls;
create table urls (
  id integer primary key autoincrement,
  url string not null,
  short string,
  count integer default 0
);
