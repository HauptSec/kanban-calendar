FROM nginx:1.29-alpine

RUN apk add --no-cache openssl

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/10-self-signed-cert.sh /docker-entrypoint.d/
COPY index.html /usr/share/nginx/html/

EXPOSE 8001
