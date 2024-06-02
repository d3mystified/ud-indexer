# Usenet Drive Prowlarr Indexer

A Prowlarr indexer for Usenet Drive nzbs.

## Docker Compose

This will deploy 2 services:

1. `ud-producer` is responsible for tracking nzbs into a SQLite DB. On startup it will scan all existing nzbs, as well as monitor FS events for newly created nzbs.
2. `ud-indexer` is a web server that allows for searching and downloading of nzbs.

```
ud-producer:
  container_name: ud-producer
  build:
   context: /path/to/clone/of/ud-indexer/
   dockerfile: Dockerfile.producer
  networks:
    - internal
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
  networks:
    - internal
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
  ports:
    - 7990:7990
  restart: always

```

## Prowlarr indexer

```
---
id: udindexer
name: UD Indexer
description: "Searches UD NZBs"
language: en-US
type: public
encoding: UTF-8
followredirect: false
testlinktorrent: false
requestDelay: 20
links:
  - http://$YOUR_IP:7990/
caps:
  categories:
    Movies: Movies
    TV: TV

  modes:
    search: [q]
    movie-search: [q, imdbid]
    tv-search: [q, imdbid, season]
  allowrawsearch: false

search:
  headers:
    User-Agent:
      [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0",
      ]
  paths:
    - path: "{{ if .Query.IMDBID }}search/movies/{{ .Query.IMDBID }}{{ else }}search/movies/title/{{ .Keywords }}{{ end }}"
      method: get
      response:
        type: json
        noResultsMessage: '"results": []'
      categories: [Movies]
    - path: "{{ if .Query.IMDBID }}search/shows/{{ .Query.IMDBID }}/{{ .Query.Season }}{{ else }}search/shows/title/{{ .Keywords }}{{ end }}"
      method: get
      response:
        type: json
        noResultsMessage: '"results": []'
      categories: [TV]

  rows:
    selector: results
    missingAttributeEqualsNoResults: true

  fields:
    title:
      selector: name
    category_is_tv_show:
      text: "{{ .Result.name }}"
      filters:
        - name: regexp
          args: "\\b(S\\d+(?:E\\d+)?)\\b"
    category:
      text: "{{ if .Result.category_is_tv_show }}TV{{ else }}Movies{{ end }}"
    year:
      selector: name
      filters:
        - name: regexp
          args: "(\\b(19|20)\\d\\d\\b)"
    infohash:
      selector: hash
    size:
      selector: raw_size
      filters:
        - name: append
          args: "B"
```