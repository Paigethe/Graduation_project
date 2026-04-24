#!/usr/bin/env bash
set -euo pipefail

echo "[mysql-init] enforcing utf8mb4 / utf8mb4_unicode_ci on database: ${MYSQL_DATABASE}"

mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" <<SQL
ALTER DATABASE \`${MYSQL_DATABASE}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
SQL

