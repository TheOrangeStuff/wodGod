#!/bin/bash
set -e

# Run SQL files in order: migrations, functions, seeds
# Postgres docker-entrypoint-initdb.d does not recurse into subdirectories,
# so this script handles the correct ordering.

for dir in /docker-entrypoint-initdb.d/sql/migrations \
           /docker-entrypoint-initdb.d/sql/functions \
           /docker-entrypoint-initdb.d/sql/seeds; do
    if [ -d "$dir" ]; then
        for f in "$dir"/*.sql; do
            if [ -f "$f" ]; then
                echo "Running: $f"
                psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$f"
            fi
        done
    fi
done
