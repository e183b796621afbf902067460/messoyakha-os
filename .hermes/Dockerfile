FROM nousresearch/hermes-agent:v2026.8.13

ENV PATH="/root/.local/bin:${PATH}"

USER root
RUN apt-get update \
    && apt-get install -y git curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code
RUN curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh \
    && codegraph init \
    && codegraph sync

WORKDIR /skills
RUN git clone --branch v6.3.0 https://github.com/obra/superpowers.git

USER hermes
