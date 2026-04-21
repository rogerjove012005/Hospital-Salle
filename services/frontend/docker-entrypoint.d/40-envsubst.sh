#!/bin/sh
set -eu

API_BASE_URL="${API_BASE_URL:-/api}"

export API_BASE_URL

envsubst '${API_BASE_URL}' < /opt/nginx/default.conf.template > /etc/nginx/conf.d/default.conf
envsubst '${API_BASE_URL}' < /usr/share/nginx/html/config.js.template > /usr/share/nginx/html/config.js
