FROM postgres:18-alpine

RUN apk add --no-cache \
    bash \
    curl \
    wget \
    zip \
    rclone

COPY restore.sh /restore.sh

RUN chmod +x /restore.sh

ENTRYPOINT ["/restore.sh"]