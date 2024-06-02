from flask import Flask, jsonify, send_file, abort
import logging
import os
import sqlite3


app = Flask(__name__)


if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)


nzbs_root_dir = os.environ.get('NZBS_DIR')
config_dir = "/config"
db_name = "nzbs.db"
table_name = "nzbs"
db_path = os.path.join(config_dir, db_name)

MTYPE_MOVIE = "movie"
MTYPE_SHOW = "show"


class NZB(object):

  def __init__(self):
    pass

  def new_from(
    self, filename, name, mtype, raw_size, title, year, tmdb_year, season, episode,
      tmdb_id, tmdb_original_name, tmdb_name, tmdb_release_date):
    self.filename = filename
    self.name = name
    self.mtype = mtype
    self.raw_size = raw_size
    self.title = title
    self.year = year
    self.tmdb_year = tmdb_year
    self.season = season
    self.episode = episode
    self.tmdb_id = tmdb_id
    self.tmdb_original_name = tmdb_original_name
    self.tmdb_name = tmdb_name
    self.tmdb_release_date = tmdb_release_date


if __name__ != '__main__':
  gunicorn_logger = logging.getLogger('gunicorn.error')
  app.logger.handlers = gunicorn_logger.handlers
  app.logger.setLevel(gunicorn_logger.level)


@app.route('/download/<filename>')
def download_nzb(filename):
  app.logger.info('New download request for %s', filename)
  # Check if file exists on disk
  for root, _, files in os.walk(nzbs_root_dir):
    if filename in files:
      full_path = os.path.join(root, filename)
      app.logger.debug("Found %s at path %s", filename, full_path)
      return send_file(full_path, as_attachment=True)
  abort(404)


@app.route("/search/shows/<imdbid>/<seasonnum>")
def search_shows_with_imdb(imdbid, seasonnum):
  app.logger.info('New show search request for %s, Season %s', imdbid, seasonnum)
  with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    query = f"SELECT * FROM {table_name} WHERE mtype='{MTYPE_SHOW}' AND imdb_id='{imdbid}' AND season={seasonnum}"
    app.logger.debug("Executing query %s", query)
    cursor.execute(query)
    rows = cursor.fetchall()
    return jsonify({"results": rows_to_dicts(cursor, rows)})


@app.route("/search/movies/<imdbid>")
def search_movies_with_imdb(imdbid):
  app.logger.info('New movie search request for %s', imdbid)
  with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    query = f"SELECT * FROM {table_name} WHERE mtype='{MTYPE_MOVIE}' AND imdb_id='{imdbid}'"
    app.logger.debug("Executing query %s", query)
    cursor.execute(query)
    rows = cursor.fetchall()
    return jsonify({"results": rows_to_dicts(cursor, rows)})


# This is needed to make prowlarr tests happy
@app.route("/search/shows/title/")
def search_shows_with_title_test():
  app.logger.info('New show search request for testing')
  with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    query = f"SELECT * FROM {table_name} WHERE mtype='{MTYPE_SHOW}' ORDER BY RANDOM() LIMIT 1;"
    app.logger.debug("Executing query %s", query)
    cursor.execute(query)
    rows = cursor.fetchall()
    return jsonify({"results": rows_to_dicts(cursor, rows)})


# This is needed to make prowlarr tests happy
@app.route("/search/movies/title/")
def search_movies_with_title_test():
  app.logger.info('New movie search request for testing')
  with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    query = f"SELECT * FROM {table_name} WHERE mtype='{MTYPE_MOVIE}' ORDER BY RANDOM() LIMIT 1;"
    app.logger.debug("Executing query %s", query)
    cursor.execute(query)
    rows = cursor.fetchall()
    return jsonify({"results": rows_to_dicts(cursor, rows)})


@app.route("/search/shows/title/<title>")
def search_shows_with_title(title):
  app.logger.info('New show search request for %s', title)
  with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    query = f"SELECT * FROM {table_name} WHERE mtype='{MTYPE_SHOW}' AND lower(tmdb_name)=lower('{title}')"
    app.logger.debug("Executing query %s", query)
    cursor.execute(query)
    rows = cursor.fetchall()
    return jsonify({"results": rows_to_dicts(cursor, rows)})


@app.route("/search/movies/title/<title>")
def search_movies_with_title(title):
  app.logger.info('New movie search request for %s', title)
  with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    query = f"SELECT * FROM {table_name} WHERE mtype='{MTYPE_MOVIE}' AND lower(tmdb_name)=lower('{title}')"
    app.logger.debug("Executing query %s", query)
    cursor.execute(query)
    rows = cursor.fetchall()
    return jsonify({"results": rows_to_dicts(cursor, rows)})


def rows_to_dicts(cursor, rows):
  column_names = [desc[0] for desc in cursor.description]
  data = []
  for row in rows:
    # Zip column names and row values to create a dictionary
    data.append(dict(zip(column_names, row)))
  return data


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=7990)
