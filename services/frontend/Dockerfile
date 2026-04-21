FROM nginx:1.27-alpine

RUN apk add --no-cache gettext

# Keep our nginx template OUTSIDE /etc/nginx/templates to avoid double-rendering
# by the stock nginx entrypoint (which can break the /api proxy config).
COPY default.conf.template /opt/nginx/default.conf.template
COPY docker-entrypoint.d/40-envsubst.sh /docker-entrypoint.d/40-envsubst.sh
RUN chmod +x /docker-entrypoint.d/40-envsubst.sh

COPY public /usr/share/nginx/html

