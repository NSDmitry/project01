---
title: "Running the project locally"
status: accepted
tags:
  - "onboarding"
---

## Prerequisites
- Python 3.11

## Install
```sh
python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## Run locally
```sh
docker compose up -d db redis
./run.sh
```

## Test
```sh
docker compose -f docker-compose.test.yml up -d
IS_TEST=true pytest -s -v
```