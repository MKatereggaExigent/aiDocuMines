#!/usr/bin/env bash

# All apps, include Python field class and DB column type
python manage.py list_model_info --field-class --db-type > MODEL_INFO_FULL.txt


# ERD for ALL installed apps
python manage.py graph_models -a -g -o models.png

