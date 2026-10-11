#!/usr/bin/env bash
# Source this file from a Bash notebook to prepare matching published artifacts.
export WORKSPACE=${WORKSPACE:-/workspace/zarr-cloud-native-format}
export APPLICATION_PACKAGE_VERSION=${APPLICATION_PACKAGE_VERSION:-2.0.0}
export RUNTIME=${RUNTIME:-$WORKSPACE/runs/$APPLICATION_PACKAGE_VERSION}
export PACKAGE_DIRECTORY="$RUNTIME/packages"
python "$WORKSPACE/scripts/prepare-practice-labs.py" --version "$APPLICATION_PACKAGE_VERSION" --destination "$PACKAGE_DIRECTORY" || return $?
export CWL_PACKAGE="$PACKAGE_DIRECTORY/app-water-bodies.cwl"
export CONSUMER_PACKAGE="$PACKAGE_DIRECTORY/app-water-bodies-occurrence.cwl"
cd "$RUNTIME" || return $?
# Select Podman on a workstation or Calrissian on any configured Kubernetes cluster.
run_cwl() {
    case "${CWL_RUNNER:-podman}" in
        podman) cwltool --podman "$@" ;;
        docker) cwltool "$@" ;;
        calrissian)
            "${CALRISSIAN_BIN:-calrissian}" --max-cores "${CALRISSIAN_MAX_CORES:-2}" --max-ram "${CALRISSIAN_MAX_RAM:-6G}" "$@"
            ;;
        *) printf 'Unknown CWL_RUNNER: %s\n' "$CWL_RUNNER" >&2; return 1 ;;
    esac
}
