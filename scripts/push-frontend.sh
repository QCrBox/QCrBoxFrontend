#!/usr/bin/env bash
#
# Build and push the QCrBoxFrontend server image to GHCR.
#
# Usage:
#   bash scripts/push-frontend.sh <version> [--tag-latest]
#
# Examples:
#   bash scripts/push-frontend.sh 0.2.0
#   bash scripts/push-frontend.sh 0.2.0 --tag-latest
#
# --tag-latest  After pushing the versioned image, also push it as :latest.
#
# Prerequisites:
#   docker login ghcr.io -u <github-username> -p <PAT with write:packages>

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
FRONTEND_DIR=$(cd "$SCRIPT_DIR/.." && pwd)

REPO=ghcr.io/qcrbox

VERSION=${1:?Usage: $0 <version> [--tag-latest]  e.g.  $0 0.2.0}
TAG_LATEST=0
shift
for arg in "$@"; do
    case "$arg" in
        --tag-latest) TAG_LATEST=1 ;;
        *) echo "ERROR: unknown argument '$arg'" >&2; exit 1 ;;
    esac
done

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "ERROR: version must be X.Y.Z (e.g. 0.2.0), got: $VERSION" >&2
    exit 1
fi

IMAGE="$REPO/qcrboxfrontend-server:$VERSION"

echo "==> Building $IMAGE"
docker build \
    -f "$FRONTEND_DIR/docker/Dockerfile" \
    -t "$IMAGE" \
    "$FRONTEND_DIR"

echo "==> Pushing $IMAGE"
docker push "$IMAGE"

if [ "$TAG_LATEST" -eq 1 ]; then
    echo "==> Also tagging and pushing as latest"
    docker tag "$IMAGE" "$REPO/qcrboxfrontend-server:latest"
    docker push "$REPO/qcrboxfrontend-server:latest"
fi

echo ""
echo "==> Done. Frontend image pushed as $IMAGE"
