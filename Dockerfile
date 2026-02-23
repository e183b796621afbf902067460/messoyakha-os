FROM python:3.10-slim

ARG TA_LIB_VERSION=0.6.4
ARG PREFIX=/tmp/build_artifacts/ta-lib_${TA_LIB_VERSION}

ENV DEBIAN_FRONTEND=noninteractive \
    TA_LIB_VERSION=${TA_LIB_VERSION} \
    PREFIX=${PREFIX}

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        build-essential autoconf automake libtool \
        wget curl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY .ta-lib.sh /usr/local/bin/.ta-lib.sh
RUN chmod +x /usr/local/bin/.ta-lib.sh
RUN /usr/local/bin/.ta-lib.sh

WORKDIR /code

COPY ./pyproject.toml /code/pyproject.toml
COPY ./poetry.lock /code/poetry.lock

ENV VIRTUAL_ENV=/code/src/venv \
    PATH="/code/src/venv/bin:${PATH}" \
    PYTHONPATH=${PYTHONPATH}:/code/src \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

ARG POETRY_VERSION=1.7.1

ENV TA_LIBRARY_PATH=$PREFIX/lib
ENV TA_INCLUDE_PATH=$PREFIX/include

RUN python3.10 -m venv --system-site-packages $VIRTUAL_ENV \
    && pip3 install poetry~=$POETRY_VERSION \
    && pip3 install ta-lib==$TA_LIB_VERSION \
    && poetry install -vvv --no-interaction --no-root \
    && rm -rf /root/.cache/pypoetry

RUN pip3 install -e "git+https://github.com/elliottech/lighter-python.git#egg=lighter-sdk"

COPY ./src /code/src
