### Dockerfile
FROM odoo:19.0

USER root

RUN apt-get update -o Acquire::Retries=3 \
    && apt-get install -y --no-install-recommends \
        gettext-base \
        postgresql-client \
        locales \
    && echo "en_US.UTF-8 UTF-8" > /etc/locale.gen \
    && locale-gen \
    && update-locale LANG=en_US.UTF-8 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --break-system-packages --ignore-installed -r /tmp/requirements.txt

COPY --chown=odoo:odoo config/odoo.conf /etc/odoo/odoo.conf.template

COPY --chown=odoo:odoo custom-addons/ /mnt/custom-addons/

COPY --chown=odoo:odoo entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh
RUN chmod 640 /etc/odoo/odoo.conf.template

USER odoo

EXPOSE 8069

ENTRYPOINT ["/entrypoint.sh"]
