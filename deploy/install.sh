#!/usr/bin/env bash
# Elmer — one-shot LXC installer. Clone the repo, run this, hit it on your port.
#
#   git clone <repo> /opt/elmer && cd /opt/elmer && sudo ./deploy/install.sh
#
# What it does (Debian/Ubuntu LXC):
#   1. installs Docker + the compose plugin (if missing)
#   2. writes .env (port, optional Anthropic key) if absent
#   3. builds the image and, on first run, reconstructs the DBs (one per
#      qualification): fetch the free ISED banks -> ingest -> validate ->
#      import the committed explanation seeds (no paid re-batch)
#   4. starts the container; prints the URL
#
# Re-running is safe: existing data/hamstudy.db / hamstudy_advanced.db are preserved
# (your attempts + explanations are never rebuilt); a missing one is built.
# Override the port:  PORT=80 sudo ./deploy/install.sh
set -euo pipefail

PORT="${PORT:-80}"
BIND_IP="${BIND_IP:-0.0.0.0}"

# repo root = parent of this script's dir
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(pwd)"
echo "==> Elmer install from ${REPO} (port ${PORT})"

SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

# --- 1. Docker + compose plugin ------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  echo "==> Installing Docker..."
  curl -fsSL https://get.docker.com | $SUDO sh
  $SUDO systemctl enable --now docker || true
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "==> Installing docker compose plugin..."
  $SUDO apt-get update -y && $SUDO apt-get install -y docker-compose-plugin
fi
DC="$SUDO docker compose"

# --- 2. .env -------------------------------------------------------------------
if [ ! -f .env ]; then
  echo "==> Creating .env"
  KEY=""
  if [ -t 0 ]; then
    read -r -s -p "Anthropic API key (optional — blank runs deterministic + cached explanations only): " KEY
    echo
  fi
  {
    echo "# Elmer environment — never commit this file"
    echo "ANTHROPIC_API_KEY=${KEY}"
    echo "PORT=${PORT}"
    echo "BIND_IP=${BIND_IP}"
  } > .env
  chmod 600 .env
else
  echo "==> .env already present — leaving it as-is"
fi

# --- 3. build image ------------------------------------------------------------
echo "==> Building image..."
$DC build

# --- 4. first-run DB build (preserve existing DBs) -----------------------------
# One store per qualification: Basic (/) and Advanced (/advanced). References are
# fetched + ingested in one ephemeral container; data/ is a volume so the DBs persist.
mkdir -p data
NEED_FETCH=0
[ -f data/hamstudy.db ] || NEED_FETCH=1
[ -f data/hamstudy_advanced.db ] || NEED_FETCH=1
if [ "$NEED_FETCH" = 1 ]; then
  echo "==> Fetching ISED source material..."
  $DC run --rm elmer python -m app.db.fetch_sources
fi
for Q in basic advanced; do
  DB="data/hamstudy.db"; [ "$Q" = advanced ] && DB="data/hamstudy_advanced.db"
  if [ ! -f "$DB" ]; then
    echo "==> Building ${Q} database (ingest -> validate -> import explanations)..."
    $DC run --rm elmer sh -c "\
      python -m app.db.ingest --qual ${Q} && \
      python -m app.db.validate --qual ${Q} && \
      python -m app.coaching.explain_batch --qual ${Q} import"
  else
    echo "==> ${DB} exists — preserving it (no rebuild, no re-batch)"
  fi
done

# --- 5. up ---------------------------------------------------------------------
echo "==> Starting Elmer..."
$DC up -d

# --- 6. systemd unit (start on boot) ------------------------------------------
if command -v systemctl >/dev/null 2>&1; then
  echo "==> Installing systemd unit (start on boot)..."
  DOCKER_BIN="$(command -v docker)"
  sed -e "s|__ELMER_DIR__|${REPO}|g" -e "s|__DOCKER__|${DOCKER_BIN}|g" deploy/elmer.service \
    | $SUDO tee /etc/systemd/system/elmer.service >/dev/null
  $SUDO systemctl daemon-reload
  $SUDO systemctl enable elmer.service
  echo "    enabled elmer.service — the stack will come up on boot"
else
  echo "==> systemd not found; relying on the container's restart policy"
fi

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
FQDN="$(hostname -f 2>/dev/null || hostname)"
echo
echo "==> Elmer is up. Reach it at:"
echo "    http://${IP}:${PORT}"
echo "    http://${FQDN}:${PORT}   (via your local DNS)"
echo "    http://${FQDN}:${PORT}/advanced   (Advanced track — separate store)"
echo
echo "    health:  curl http://localhost:${PORT}/api/health"
echo "    logs:    $SUDO docker compose logs -f"
echo "    boot:    $SUDO systemctl status elmer    (starts automatically on reboot)"
echo
echo "Reminder: set a hard monthly spend limit in the Anthropic Console before heavy AI use."
