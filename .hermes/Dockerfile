FROM nousresearch/hermes-agent:v2026.8.13

ENV PATH="/root/.local/bin:${PATH}"
ENV HERMES_WRITE_SAFE_ROOT="/code"

USER root

RUN mkdir -p /code && chown -R hermes:hermes /code

RUN apt-get update \
    && apt-get install -y git curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /skills
RUN git clone --branch v6.3.0 https://github.com/obra/superpowers.git

RUN chown -R root:root /skills /opt/data/memories /opt/data/skills \
    && chmod -R 555 /skills /opt/data/memories /opt/data/skills

WORKDIR /code
RUN curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh \
    && codegraph init \
    && codegraph sync

USER hermes

COPY ./home /code/home
COPY ./lib /code/lib

COPY ./pyproject.toml \
    ./uv.lock \
    ./Makefile \
    ./.gitignore \
    ./.pre-commit-config.yaml \
    ./AGENTS.md \
    ./codegraph.json \
    ./README.md \
    /code/

RUN make sync
