#!/usr/bin/env bash
# Install unzzz as a systemd service on Debian/Raspberry Pi OS.
# Run from the repository root: sudo ./install.sh
set -euo pipefail

INSTALL_DIR="/opt/unzzz"
DATA_DIR="/var/lib/unzzz"
BIND="0.0.0.0"
PORT="8888"
WITH_AUDIO="no"
SERVICE="unzzz"

usage() {
  cat <<EOF
Usage: sudo ./install.sh [options]

  --dir DIR        install code to DIR          (default: /opt/unzzz)
  --data-dir DIR   database and beep file       (default: /var/lib/unzzz)
  --port PORT      HTTP port                    (default: 8888)
  --bind ADDR      listen address               (default: 0.0.0.0)
  --with-audio     apt-get install alsa-utils if no player is found
  -h, --help       this help

The service runs as the system user "unzzz" and listens on the LAN. After it
starts, open http://<pi-address>:$PORT/ and set the admin password.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) INSTALL_DIR="$2"; shift 2 ;;
    --data-dir) DATA_DIR="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --bind) BIND="$2"; shift 2 ;;
    --with-audio) WITH_AUDIO="yes"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root: sudo ./install.sh" >&2
  exit 1
fi
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || (( PORT < 1 || PORT > 65535 )); then
  echo "Invalid port: $PORT" >&2
  exit 1
fi

if ! command -v python3 >/dev/null; then
  echo "python3 is required (Raspberry Pi OS ships it)." >&2
  exit 1
fi
PYVER="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
python3 - <<'PY' || { echo "unzzz needs Python 3.9+ with zoneinfo (Raspberry Pi OS Bookworm or newer)." >&2; exit 1; }
import sys, zoneinfo, sqlite3
raise SystemExit(0 if sys.version_info >= (3, 9) else 1)
PY
echo "Using Python ${PYVER}"

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$INSTALL_DIR" && "$(cd "$SOURCE_DIR" && pwd -P)" == "$(cd "$INSTALL_DIR" && pwd -P)" ]]; then
  echo "Run install.sh from a separate checkout, not from $INSTALL_DIR itself." >&2
  exit 1
fi

if ! id -u unzzz >/dev/null 2>&1; then
  useradd --system --home-dir "$INSTALL_DIR" --shell /usr/sbin/nologin --user-group unzzz
  echo "Created system user unzzz"
fi
if getent group audio >/dev/null; then
  usermod -aG audio unzzz
fi

install -d -m 0755 "$INSTALL_DIR"
install -d -m 0750 -o unzzz -g unzzz "$DATA_DIR"

# Code only; never touch $DATA_DIR on upgrade.
rm -rf "$INSTALL_DIR/unzzz"
cp -a "$SOURCE_DIR/unzzz" "$INSTALL_DIR/unzzz"
install -d -m 0755 "$INSTALL_DIR/bin" "$INSTALL_DIR/deploy"
install -m 0755 "$SOURCE_DIR/bin/unzzz" "$INSTALL_DIR/bin/unzzz"
install -m 0644 "$SOURCE_DIR/README.md" "$INSTALL_DIR/README.md"
install -m 0644 "$SOURCE_DIR/LICENSE" "$INSTALL_DIR/LICENSE"
install -m 0644 "$SOURCE_DIR/deploy/unzzz.service" "$INSTALL_DIR/deploy/unzzz.service"
install -d -m 0755 "$INSTALL_DIR/docs"
cp -a "$SOURCE_DIR/docs/." "$INSTALL_DIR/docs/"
find "$INSTALL_DIR/unzzz" -name '__pycache__' -type d -prune -exec rm -rf {} +
chown -R root:root "$INSTALL_DIR"
chmod -R u=rwX,go=rX "$INSTALL_DIR"

# The service user must be able to read the code and write only its data.
chown -R unzzz:unzzz "$DATA_DIR"

PLAYER=""
for candidate in aplay paplay mpv ffplay play; do
  if command -v "$candidate" >/dev/null; then PLAYER="$candidate"; break; fi
done
if [[ -z "$PLAYER" ]]; then
  if [[ "$WITH_AUDIO" == "yes" ]]; then
    echo "Installing alsa-utils for aplay…"
    apt-get update -qq
    apt-get install -y --no-install-recommends alsa-utils
    PLAYER="aplay"
  else
    echo "WARNING: no audio player found. Install one with:"
    echo "  sudo apt install alsa-utils        # aplay, lightest"
    echo "or re-run with --with-audio."
    echo "You can still finish the panel setup; sound will be silent until a player exists."
  fi
fi
[[ -n "$PLAYER" ]] && echo "Audio player: $PLAYER"

UNIT_SRC="$SOURCE_DIR/deploy/unzzz.service"
UNIT_DST="/etc/systemd/system/${SERVICE}.service"
sed -e "s|@INSTALL_DIR@|$INSTALL_DIR|g" \
    -e "s|@DATA_DIR@|$DATA_DIR|g" \
    -e "s|@BIND@|$BIND|g" \
    -e "s|@PORT@|$PORT|g" \
    "$UNIT_SRC" > "$UNIT_DST"
chmod 0644 "$UNIT_DST"

systemctl daemon-reload
systemctl enable "$SERVICE" >/dev/null
systemctl restart "$SERVICE"

for _ in $(seq 1 10); do
  systemctl is-active --quiet "$SERVICE" && break
  sleep 1
done
if ! systemctl is-active --quiet "$SERVICE"; then
  echo "Service failed to start. Recent logs:" >&2
  journalctl -u "$SERVICE" -n 30 --no-pager >&2 || true
  exit 1
fi

LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
LAN_IP="${LAN_IP:-<pi-address>}"
cat <<EOF

unzzz is running as a systemd service.

  Panel:     http://${LAN_IP}:${PORT}/
  Data:      ${DATA_DIR}
  Service:   systemctl status ${SERVICE}
  Logs:      journalctl -u ${SERVICE} -f
  Restart:   sudo systemctl restart ${SERVICE}
  Password:  sudo -u unzzz ${INSTALL_DIR}/bin/unzzz passwd --data-dir ${DATA_DIR}

Open the panel from a phone or laptop on the same network and set the admin
password. Then add people and create an alarm.

Sound check:
  sudo -u unzzz ${INSTALL_DIR}/bin/unzzz doctor --data-dir ${DATA_DIR}
  aplay -l                          # list ALSA cards (run as your desktop user too)
  speaker-test -t sine -f 440 -c 1  # if aplay is installed
  alsamixer                         # unmute / raise PCM volume
EOF
