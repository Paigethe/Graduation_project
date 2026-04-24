#!/usr/bin/env bash
set -euo pipefail

API="${API:-http://127.0.0.1:52517/api}"

echo "API=${API}"

TOKEN_STUDENT=$(curl -s "$API/auth/token/" \
  -H 'Content-Type: application/json' \
  -d '{"username":"student1","password":"123456"}' | jq -r .access)

echo "## Health"
curl -s -o /dev/null -w "time_total=%{time_total}\n" "$API/health/"

echo "## Questionnaires"
curl -s -o /dev/null -w "time_total=%{time_total}\n" \
  -H "Authorization: Bearer $TOKEN_STUDENT" \
  "$API/surveys/questionnaires/"

echo "## Submit Questionnaire"
Q_ID=$(curl -s "$API/surveys/questionnaires/" -H "Authorization: Bearer $TOKEN_STUDENT" | jq -r '.results[0].id')
curl -s -o /dev/null -w "time_total=%{time_total}\n" \
  -H "Authorization: Bearer $TOKEN_STUDENT" \
  -H 'Content-Type: application/json' \
  -X POST "$API/surveys/questionnaires/$Q_ID/submit/" \
  -d '{"answers":{"1":4,"2":4,"3":3,"4":3,"5":4,"6":4,"7":3,"8":3,"9":2,"10":2}}'

echo "## Assessments"
curl -s -o /dev/null -w "time_total=%{time_total}\n" \
  -H "Authorization: Bearer $TOKEN_STUDENT" \
  "$API/assessments/results/"
