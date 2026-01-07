FROM docker.io/library/python:3.12.11-bookworm@sha256:bea386df48d7ee07eed0a1f3e6f9d5c0292c228b8d8ed2ea738b7a57b29c4470

RUN pip install --no-cache-dir odc-stac zarr loguru click && \
    python -c "from odc.stac import stac_load"

ADD app.py /app/app.py

ENTRYPOINT []
