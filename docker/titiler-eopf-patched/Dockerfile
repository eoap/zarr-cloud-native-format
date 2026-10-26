# Pin the last compatible local-store API instead of the moving STAC-API main.
ARG TITILER_BASE_IMAGE=ghcr.io/eopf-explorer/titiler-eopf@sha256:4da71e3a9f66be1abc49c30628fa56ad307242bc5878121c0ef9909bbb54354e
FROM ${TITILER_BASE_IMAGE}

RUN apt-get update && apt-get install -y --only-upgrade ca-certificates && \
    update-ca-certificates && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir --upgrade "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70" && \
    python -m pip install --no-cache-dir --upgrade "certifi>=2026.10.19"

COPY docker/titiler-eopf-patched/patch_titiler_eopf.py /tmp/patch_titiler_eopf.py

RUN python /tmp/patch_titiler_eopf.py && rm -f /tmp/patch_titiler_eopf.py
