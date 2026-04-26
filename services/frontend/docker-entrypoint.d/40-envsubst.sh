#!/bin/sh
set -eu

API_BASE_URL="${API_BASE_URL:-/api}"
MAILPIT_UI_URL="${MAILPIT_UI_URL:-http://localhost:8025}"

export API_BASE_URL
export MAILPIT_UI_URL

envsubst '${API_BASE_URL}' < /opt/nginx/default.conf.template > /etc/nginx/conf.d/default.conf
envsubst '${API_BASE_URL} ${MAILPIT_UI_URL}' < /usr/share/nginx/html/config.js.template > /usr/share/nginx/html/config.js
