FROM postgres:18-alpine

RUN apk add --no-cache \
    bash \
    curl \
    wget \
    zip \
    rclone

COPY backup.sh /backup.sh

RUN chmod +x /backup.sh

ENTRYPOINT ["/backup.sh"]