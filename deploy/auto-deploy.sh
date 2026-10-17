#!/bin/sh
# Pull main from GitHub and rebuild the container when it has new commits.
# Run by weekboard-deploy.timer; pass --force to rebuild even if nothing changed.
# The server checkout is deploy-only: local edits to tracked files are discarded.
set -eu
cd "$(dirname "$0")/.."

git fetch -q origin main
if [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] && [ "${1:-}" != "--force" ]; then
  exit 0
fi

echo "Deploying $(git rev-parse --short origin/main): $(git log -1 --format=%s origin/main)"
git reset -q --hard origin/main
docker compose up -d --build
docker image prune -f >/dev/null  # drop the superseded image layers
