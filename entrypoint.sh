#!/bin/sh
set -e

aerich upgrade
exec python run.py
