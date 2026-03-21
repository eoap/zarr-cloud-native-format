FROM ghcr.io/eopf-explorer/titiler-eopf:main

COPY docker/titiler-eopf-patched/patch_titiler_eopf.py /tmp/patch_titiler_eopf.py

RUN python /tmp/patch_titiler_eopf.py && rm -f /tmp/patch_titiler_eopf.py
