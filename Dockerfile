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
COPY ./uv.lock /code/uv.lock

ENV VIRTUAL_ENV=/code/src/venv \
    PATH="/code/src/venv/bin:${PATH}" \
    PYTHONPATH=${PYTHONPATH}:/code/src \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

ENV UV_VERSION=0.11.1
ENV UV_VENV_CLEAR=1

ENV TA_LIBRARY_PATH=$PREFIX/lib
ENV TA_INCLUDE_PATH=$PREFIX/include

RUN python3.10 -m venv --system-site-packages $VIRTUAL_ENV \
    && pip3 install uv~=$UV_VERSION \
    && pip3 install ta-lib==$TA_LIB_VERSION \
    && source $VIRTUAL_ENV/bin/activate \
    && uv sync

COPY ./src /code/src
