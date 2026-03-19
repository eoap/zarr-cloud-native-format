# Stage 1: Build stage
FROM rockylinux:9.3-minimal AS build

# Install necessary build tools
RUN microdnf install -y curl tar

# Download the hatch tar.gz file from GitHub
RUN curl -L https://github.com/pypa/hatch/releases/latest/download/hatch-x86_64-unknown-linux-gnu.tar.gz -o /tmp/hatch-x86_64-unknown-linux-gnu.tar.gz

# Extract the hatch binary
RUN tar -xzf /tmp/hatch-x86_64-unknown-linux-gnu.tar.gz -C /tmp/

# Stage 2: Final stage
FROM rockylinux:9.3-minimal

# Install runtime dependencies
RUN microdnf install -y --nodocs nodejs && \
    microdnf clean all

# Set up a default user and home directory
ENV HOME=/home/neo

# Create a user with UID 1001, group root, and a home directory
RUN useradd -u 1001 -r -g 0 -m -d ${HOME} -s /sbin/nologin \
        -c "Default User" neo && \
    mkdir -p /app && \
    mkdir -p /prod && \
    chown -R 1001:0 /app && \
    chmod g+rwx ${HOME} /app

# Copy the hatch binary from the build stage
COPY --from=build /tmp/hatch /usr/bin/hatch

# Ensure the hatch binary is executable
RUN chmod +x /usr/bin/hatch

RUN microdnf install -y expat && microdnf clean all

# Switch to the non-root user
USER neo

# Copy the application files into the /app directory
COPY --chown=1001:0 . /app
WORKDIR /app

# Set up virtual environment paths
ENV VIRTUAL_ENV=/app/envs/prod
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV XDG_DATA_HOME=/app/.hatch/share
ENV XDG_CACHE_HOME=/app/.hatch/cache
ENV XDG_CONFIG_HOME=/app/.hatch/config

# Prune any existing environments and create a new production environment
RUN hatch env prune && \
    hatch env create prod && \
    #rm -fr /app/.git /app/.pytest_cache && \
    rm -fr ~/.local && \
    stac-collection --help

WORKDIR /app