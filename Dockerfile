FROM python:3.9-slim
LABEL maintainer="James Turk <dev@jamesturk.net>"

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING='utf-8' LANG='C.UTF-8'

RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
      git \
      build-essential \
      curl \
      unzip \
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
      wget \
      unzip \
      mdbtools && \
      apt-get clean && \
      rm -rf /var/lib/apt/lists/*

WORKDIR /opt/openstates/openstates/
ADD pyproject.toml /opt/openstates/openstates
ADD poetry.lock /opt/openstates/openstates

ENV PYTHONPATH=./scrapers

RUN pip --no-cache-dir --disable-pip-version-check install poetry \
    && poetry install -q \
    && rm -r /root/.cache/pypoetry/cache /root/.cache/pypoetry/artifacts/ \
    && apt-get remove -y -qq \
      build-essential \
      libpq-dev \
    && apt-get autoremove -y -qq \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ADD . /opt/openstates/openstates

ENTRYPOINT ["poetry", "run", "os-update"]
