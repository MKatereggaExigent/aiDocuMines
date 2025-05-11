#!/usr/bin/env bash

find . -type f -path "*/migrations/*.py" ! -name "__init__.py" -print -delete

find . -type f -path "*/migrations/*.pyc" -print -delete

pip uninstall django

pip install django
