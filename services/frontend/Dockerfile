FROM nginx:1.27-alpine

RUN apk add --no-cache gettext

COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY docker-entrypoint.d/40-envsubst.sh /docker-entrypoint.d/40-envsubst.sh
RUN chmod +x /docker-entrypoint.d/40-envsubst.sh

COPY public /usr/share/nginx/html

