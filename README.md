# Usenet Drive Prowlarr Indexer

A Prowlarr indexer for Usenet Drive nzbs.

## How it works

There are three components that make up this indexer:

### `ud-producer`

This is responsible for tracking nzbs created by UD into a SQLite DB. On startup it will scan all existing nzbs, as well as monitor FS events for newly created nzbs. It requires a tmdb API key.

### `ud-indexer`

This is a Newznab-compatible API server that allows for searching and downloading of nzbs.

### `ud-blackhole`

This is a script to integrate radarr/sonarr with the indexer. This script will:

- Watch `BLACKHOLE_BASE_WATCH_PATH` for incoming nzbs (dropped in arr-specific directories by the arr application)
- Search in `BLACKHOLE_UD_MOUNT_PATH` for any file that satisfies the NZB. This is the path where rclone crypt mounts NZBs.
- Create symlink in a `completed` directory pointing to the file in the crypt directory.

## Install

Container images are also available to user:

- `ghcr.io/d3mystified/ud-indexer/ud-producer:main`
- `ghcr.io/d3mystified/ud-indexer/ud-indexer:main`
- `ghcr.io/d3mystified/ud-indexer/ud-blackhole:main`

```
ud-producer:
  container_name: ud-producer
  build:
   context: /path/to/clone/of/ud-indexer/
   dockerfile: Dockerfile.producer
  user: "1000:1000"
  volumes:
    - /path/to/usenet-drive/nzbs:/nzbs
    - /path/to/config/for/database:/config
  environment:
    - NZBS_DIR=/nzbs
    - TMDB_KEY=<GET_YOUR_OWN_KEY
    - PUID=1000
    - PGID=1000
  restart: always

ud-indexer:
  container_name: ud-indexer
  build:
   context: /path/to/clone/of/ud-indexer/
   dockerfile: Dockerfile.indexer
  user: "1000:1000"
  depends_on:
    - ud-producer
  volumes:
    - /path/to/usenet-drive/nzbs:/nzbs
    - /path/to/config/for/database:/config
  environment:
    - NZBS_DIR=/nzbs
    - PUID=1000
    - PGID=1000
    - INDEXER_BASE_URL=http://$LAN_IP:7990
  ports:
    - 7990:7990
  restart: always

ud-blackhole:
  container_name: ud-blackhole
  build:
   context: /path/to/clone/of/ud-indexer/
   dockerfile: Dockerfile.blackhole
  user: "1000:1000"
  volumes:
    - /path/to/usenet-drive-crypt:/usenet-drive-crypt
    - /path/to/watch/blackhole:/blackhole-ud
  environment:
    - PUID=1000
    - PGID=1000
    - BLACKHOLE_BASE_WATCH_PATH=/blackhole-ud
    - BLACKHOLE_RADARR_PATH=radarr
    - BLACKHOLE_SONARR_PATH=sonarr
    - BLACKHOLE_UD_MOUNT_PATH=/usenet-drive-crypt
  restart: always
```
