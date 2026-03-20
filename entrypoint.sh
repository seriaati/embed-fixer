#!/bin/sh
set -e

aerich fix-migrations
aerich upgrade
exec python run.py
