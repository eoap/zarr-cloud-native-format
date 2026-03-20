FROM rockylinux/rockylinux:10.1-minimal AS builder

RUN microdnf -y update && \
    microdnf -y install curl tar python3 python3-pip python3-setuptools gcc && \
    microdnf clean all

RUN curl -L https://github.com/pypa/hatch/releases/download/hatch-v1.14.0/hatch-x86_64-unknown-linux-gnu.tar.gz \
      -o /tmp/hatch.tar.gz && \
    tar -xzf /tmp/hatch.tar.gz -C /tmp && \
    install -m 0755 /tmp/hatch /usr/local/bin/hatch && \
    rm -rf /tmp/hatch* /tmp/hatch.tar.gz

WORKDIR /src
COPY . /src

RUN hatch build -t wheel

FROM rockylinux/rockylinux:10.1-minimal AS runtime

RUN microdnf -y update && \
    microdnf -y install python3 python3-pip && \
    microdnf clean all

ENV HOME=/home/neo
RUN /usr/sbin/groupadd -g 1000 neo && \
    /usr/sbin/useradd -u 1000 -g 1000 -m -d ${HOME} -s /sbin/nologin neo && \
    mkdir -p /app && \
    chown -R 1000:1000 /app ${HOME}

USER neo
WORKDIR /app

ENV VIRTUAL_ENV=/app/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

RUN PYBIN="$(command -v python3 || command -v python)" && \
    "$PYBIN" -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir --upgrade pip

COPY --from=builder /src/dist/*.whl /app/dist/

RUN /app/venv/bin/pip install --no-cache-dir /app/dist/*.whl && \
    stac-collection --help
