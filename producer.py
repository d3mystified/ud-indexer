import logging
import LordNzb
import PTN
import os
import requests
import sqlite3
import xml.etree.ElementTree as ET
import themoviedb
from sys import stdout
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# Define logger
logger = logging.getLogger('producer')
logger.setLevel(logging.DEBUG)
logFormatter = logging.Formatter\
  ("%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s")
consoleHandler = logging.StreamHandler(stdout)
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)


nzbs_root_dir = os.environ.get('NZBS_DIR')
config_dir = "/config"
db_name = "nzbs.db"
table_name = "nzbs"
db_path = os.path.join(config_dir, db_name)

MTYPE_MOVIE = "movie"
MTYPE_SHOW = "show"

tmdb = themoviedb.TMDb(key=os.environ.get('TMDB_KEY'), language="en-US", region="US")


class NZB(object):

  def __init__(self):
    pass

  def new_from(
    self, filename, name, mtype, raw_size, title, year, tmdb_year, season, episode,
      tmdb_id, tmdb_original_name, tmdb_name, tmdb_release_date, imdb_id):
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
    self.imdb_id = imdb_id


class NzbEventHandler(FileSystemEventHandler):

    def on_created(self, event):
        logger.info(f"File '{event.src_path}' created!")
        if event.is_directory:
          logger.debug("Path is a directory. Skipping...")
          return
        if not event.src_path.endswith('.nzb'):
          logger.debug("Not a .nzb file. Skipping.")
          return
        process_single_nzb(event.src_path)


def create_db_and_table():
  # Connect to the database (creates it if it doesn't exist)
  conn = sqlite3.connect(db_path)
  logger.info("Creating database..")
  cursor = conn.cursor()

  logger.info("Creating table nzbs..")
  # Create the nzbs table (if it doesn't exist)
  create_table_query = f"""
  CREATE TABLE IF NOT EXISTS {table_name} (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      filename TEXT NOT NULL,
      name TEXT NOT NULL,
      mtype TEXT NOT NULL,
      raw_size INTEGER NOT NULL,
      title TEXT NOT NULL,
      year INTEGER,
      tmdb_year INTEGER,
      season INTEGER,
      episode TEXT,
      tmdb_id INTEGER,
      tmdb_original_name TEXT,
      tmdb_name TEXT,
      tmdb_release_date TEXT,
      imdb_id TEXT
  );
  """
  cursor.execute(create_table_query)
  conn.commit()
  logger.info("Done..")
  conn.close()


# Function to check if NZB exists by filename and raw_size
def nzb_exists(filename, raw_size):
  with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    check_query = f"""
    SELECT COUNT(*) FROM {table_name} WHERE filename = ? AND raw_size = ?
    """
    cursor.execute(check_query, (filename, raw_size))
    count = cursor.fetchone()[0]
    return count > 0


# Function to add a new entry
def add_nzb(nzbo):
  if not nzb_exists(nzbo.filename, nzbo.raw_size):
    with sqlite3.connect(db_path) as conn:
      cursor = conn.cursor()
      insert_query = f"""
      INSERT INTO {table_name} (filename, name, mtype, raw_size, title, year, tmdb_year, season, episode, tmdb_id, tmdb_original_name, tmdb_name, tmdb_release_date, imdb_id)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      """
      cursor.execute(insert_query,
                     (nzbo.filename, nzbo.name, nzbo.mtype, nzbo.raw_size,
                      nzbo.title, nzbo.year, nzbo.tmdb_year, nzbo.season,
                      nzbo.episode, nzbo.tmdb_id, nzbo.tmdb_original_name,
                      nzbo.tmdb_name, nzbo.tmdb_release_date, nzbo.imdb_id))
      conn.commit()
      logger.info(f"NZB '{nzbo.filename}' added successfully!")
  else:
    logger.info(f"NZB with filename '{nzbo.filename}' and raw_size {nzbo.raw_size} already exists.")


# Returns relative paths (to NZBS_DIR)
def load_all_nzbs():
  logger.info("Walking root dir for nzb files")
  file_set = set()
  for dir_, _, files in os.walk(nzbs_root_dir):
    for file_name in files:
      if file_name.endswith('.nzb'):
        rel_dir = os.path.relpath(dir_, nzbs_root_dir)
        rel_file = os.path.join(rel_dir, file_name)
        file_set.add(rel_file)
  logger.info("Found %d nzb files", len(file_set))
  return file_set


def process_single_nzb(file):
  filepath = file
  # Watchdog tracks absolute paths, so this is needed to handle that case.
  if not os.path.isabs(file):
    filepath = os.path.join(nzbs_root_dir, file)

  logger.debug("Processing file %s", filepath)
  with open(filepath, 'rb') as f:
    nzbo = NZB()

    nzb_metadata = parse_nzb_metadata(filepath)
    parsed_info = PTN.parse(nzb_metadata['name'])

    # Set basic metadata
    nzbo.filename = nzb_metadata['filename']
    nzbo.name = nzb_metadata['name']
    nzbo.raw_size = nzb_metadata['raw_size']
    nzbo.title = parsed_info['title']

    if nzb_exists(nzbo.filename, nzbo.raw_size):
      logger.debug("Already exists in the table.. Skipping")
      return

    nzbo.mtype = MTYPE_MOVIE
    is_tv = False
    if 'season' in parsed_info or 'month' in parsed_info or 'episode' in parsed_info:
      is_tv = True
      nzbo.mtype = MTYPE_SHOW

    # Set the year based on the file name
    nzbo.year = parsed_info.get('year', None)

    # Set season
    nzbo.season = parsed_info.get('season', None)
    if is_tv and not parsed_info.get('season', None):
      nzbo.season = 1

    # Set episode number
    if isinstance(parsed_info.get('episode', None), list):
      nzbo.episode = "".join(["E{:02d}".format(e) for e in parsed_info['episode']])
    else:
      nzbo.episode = parsed_info.get('episode', None)

    # Set TMDB values by calling the API
    nzbo.tmdb_id = None
    nzbo.tmdb_original_name = None
    nzbo.tmdb_name = None
    nzbo.tmdb_release_date = None
    nzbo.tmdb_year = None
    nzbo.imdb_id = None

    if is_tv:
      # It's a TV show
      matching_shows = tmdb.search().tv(parsed_info['title'])
      if len(matching_shows) > 0:
        show = tmdb.tv(matching_shows[0].id).details(append_to_response="external_ids")
        nzbo.tmdb_id = show.id
        nzbo.tmdb_original_name = show.original_name
        nzbo.tmdb_name = show.name
        nzbo.tmdb_release_date = show.first_air_date.strftime('%Y-%m-%d')
        nzbo.tmdb_year = show.first_air_date.year
        nzbo.imdb_id = show.external_ids.imdb_id
    else:
      # It's a movie
      matching_movies = tmdb.search().movies(parsed_info['title'])
      if len(matching_movies) > 0:
        movie = tmdb.movie(matching_movies[0].id).details(append_to_response="external_ids")
        nzbo.tmdb_id = movie.id
        nzbo.tmdb_original_name = movie.original_title
        nzbo.tmdb_name = movie.title
        nzbo.tmdb_release_date = movie.release_date.strftime('%Y-%m-%d')
        nzbo.tmdb_year = movie.release_date.year
        nzbo.imdb_id = movie.external_ids.imdb_id

    add_nzb(nzbo)


def load_nzb_data():
  logger.info("Loading nzb data")
  all_nzb_files = load_all_nzbs()
  for file in all_nzb_files:
    process_single_nzb(file)
  logger.info("Done loading nzb data")


# Function to parse metadata from nzb (replace with your XML parsing logic)
def parse_nzb_metadata(filepath):
  m = LordNzb.parser(filepath)
  return {
    'filename': m.filename,
    'name': m.name,
    'raw_size': m.raw_size
  }


if __name__ == '__main__':
  create_db_and_table()
  load_nzb_data()
  observer = Observer()
  observer.schedule(NzbEventHandler(), nzbs_root_dir, recursive=True)
  observer.start()
  try:
      while True:
          time.sleep(1)
  except KeyboardInterrupt:
      observer.stop()
  observer.join()