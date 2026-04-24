#!/usr/bin/env bash
set -euo pipefail

API="${API:-http://127.0.0.1:52517/api}"

TOKEN_STUDENT=$(curl -s "$API/auth/token/" \
  -H 'Content-Type: application/json' \
  -d '{"username":"student1","password":"123456"}' | jq -r .access)

TOKEN_COUNSELOR=$(curl -s "$API/auth/token/" \
  -H 'Content-Type: application/json' \
  -d '{"username":"counselor1","password":"123456"}' | jq -r .access)

TOKEN_COLLEGE_ADMIN=$(curl -s "$API/auth/token/" \
  -H 'Content-Type: application/json' \
  -d '{"username":"college_admin","password":"123456"}' | jq -r .access)

TOKEN_ADMIN=$(curl -s "$API/auth/token/" \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"123456"}' | jq -r .access)

echo "## Student access admin users (expect 403)"
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN_STUDENT" "$API/admin/users/"

echo "## Student access backups export (expect 403)"
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN_STUDENT" -X POST "$API/backups/export/"

echo "## Counselor access admin users (expect 403)"
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN_COUNSELOR" "$API/admin/users/"

echo "## College admin access admin users (expect 403)"
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN_COLLEGE_ADMIN" "$API/admin/users/"

echo "## Sys admin access admin users (expect 200)"
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN_ADMIN" "$API/admin/users/"
