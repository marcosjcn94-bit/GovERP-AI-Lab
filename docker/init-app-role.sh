#!/bin/sh
set -eu

psql --set=ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_password="$GOVERP_APP_PASSWORD" <<'SQL'
CREATE ROLE goverp_app LOGIN PASSWORD :'app_password';
GRANT CONNECT ON DATABASE goverp TO goverp_app;
GRANT USAGE ON SCHEMA public TO goverp_app;
ALTER DEFAULT PRIVILEGES FOR ROLE goverp_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO goverp_app;
ALTER DEFAULT PRIVILEGES FOR ROLE goverp_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO goverp_app;
SQL
