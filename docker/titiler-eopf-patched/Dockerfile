# Pin the last compatible local-store API instead of the moving STAC-API main.
ARG TITILER_BASE_IMAGE=ghcr.io/eopf-explorer/titiler-eopf@sha256:4da71e3a9f66be1abc49c30628fa56ad307242bc5878121c0ef9909bbb54354e
FROM ${TITILER_BASE_IMAGE}

COPY docker/titiler-eopf-patched/patch_titiler_eopf.py /tmp/patch_titiler_eopf.py

RUN python /tmp/patch_titiler_eopf.py && rm -f /tmp/patch_titiler_eopf.py
