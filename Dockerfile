# First, build the application in the `/app` directory.
FROM ghcr.io/astral-sh/uv:python3.13-alpine AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Then, use a final image without uv
FROM python:3.13-alpine

WORKDIR /app

# Place executables in the environment at the front of the path, set env var defaults
ENV PATH="/app/.venv/bin:$PATH"

# Install supercronic
RUN apk --no-cache add tini supercronic tzdata

COPY ./docker-entrypoint.sh ./

# Copy the application from the builder
COPY --from=builder --chown=app:app /app /app

# backwards compat entrypoint
RUN ln -s /app/docker-entrypoint.sh / \
    && addgroup --system runner && adduser --system runner --ingroup runner

VOLUME [ "/config" ]

USER runner

ENTRYPOINT ["tini", "--", "./docker-entrypoint.sh"]