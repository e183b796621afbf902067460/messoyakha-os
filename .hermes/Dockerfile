FROM nousresearch/hermes-agent:v2026.8.13

ENV PATH="/root/.local/bin:${PATH}"

ENV HERMES_WRITE_SAFE_ROOT="/code"
ARG HERMES_UID
ARG HERMES_GID

USER root

# Grant Hermes Agent same permissions as User has
RUN groupmod -g ${HERMES_GID} hermes \
    && usermod -u ${HERMES_UID} -g ${HERMES_GID} hermes \
    && mkdir -p /code \
    && chown -R ${HERMES_UID}:${HERMES_GID} /code

RUN apt-get update \
    && apt-get install -y git curl \
    && rm -rf /var/lib/apt/lists/*

# External Skills
WORKDIR /skills
RUN git clone --branch v6.3.0 https://github.com/obra/superpowers.git
RUN git clone --branch v1.13.18 https://github.com/dagster-io/skills.git dagster-skills

RUN chown -R root:root /skills \
    && chmod -R 555 /skills

RUN mkdir -p /opt/data/memories /opt/data/skills /opt/data/skills/.hub \
    && chmod -R 555 /opt/data/memories /opt/data/skills \
    && chmod -R 777 /opt/data/skills/.hub

USER ${HERMES_UID}
WORKDIR /code

# Dependencies
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

# External Tools
RUN curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh \
    && codegraph init \
    && codegraph sync
