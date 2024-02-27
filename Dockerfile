FROM python:3.9-slim
LABEL maintainer="James Turk <dev@jamesturk.net>"

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONIOENCODING='utf-8'
ENV LANG='C.UTF-8'

RUN apt-get update -qq \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
      ca-certificates \
      curl \
      wget \
      unzip \
      mdbtools \
      libpq5 \
      libgdal32 \
      build-essential \
      git \
      libssl-dev \
      libffi-dev \
      freetds-dev \
      libxml2-dev \
      libxslt-dev \
      libyaml-dev \
      poppler-utils \
      libpq-dev \
      libgdal-dev \
      libgeos-dev \
      gnupg \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update -qq \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends gh
RUN pip --no-cache-dir --disable-pip-version-check install wheel \
    && pip --no-cache-dir --disable-pip-version-check install crcmod poetry

ADD poetry.lock /opt/openstates/openstates/
ADD pyproject.toml /opt/openstates/openstates/
WORKDIR /opt/openstates/openstates/
ENV PYTHONPATH=./scrapers

RUN poetry install --no-root

ADD . /opt/openstates/openstates/

# the last step cleans out temporarily downloaded artifacts for poetry, shrinking our build
RUN poetry install \
    && rm -r /root/.cache/pypoetry/cache /root/.cache/pypoetry/artifacts/ \
    && apt-get remove -y -qq \
      build-essential \
      libpq-dev \
    && apt-get autoremove -y -qq \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV ENVIRONMENT=prod
ENV OPENSSL_CONF=/opt/openstates/openstates/openssl.cnf
ENV GOOGLE_CLOUD_PROJECT="civiqa-301113"
ENV SETTINGS_NAME="django_settings"
ENV DATABASE_URL="postgres://pgbouncer:42571allahis1@34.118.205.29:5432/civiqa-sql-db-1"
ENV VIRGINIA_FTP_USER aibrahim
ENV VIRGINIA_FTP_PASSWORD "AMXKa3Waws!XXHBirQk"
ENV NEW_YORK_API_KEY "4JRIFodoL0g6StkCPOLyu4pakrUhLdm8"
ENV DC_API_KEY "70d08774-9ba1-4108-80ce-248a3454b08b"
ENV INDIANA_API_KEY "Token 9da9a5b7d1439477b08ba5f7ebae1ace78fe658e"
ENV VERIFY_CERTS="False"
ENTRYPOINT ["poetry", "run", "os-update"]
