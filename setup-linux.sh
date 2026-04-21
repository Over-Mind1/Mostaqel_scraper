#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/venv"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found in PATH." >&2
  exit 1
fi

if ! python3 -c 'import venv' >/dev/null 2>&1; then
  echo "python3-venv is required. Install it with your system package manager and run this script again." >&2
  exit 1
fi

echo "Creating virtual environment..."
python3 -m venv "${VENV_DIR}"

echo "Upgrading pip and installing dependencies..."
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${ROOT_DIR}/requirements.txt"

if [[ ! -f "${ROOT_DIR}/.env" ]]; then
  if [[ -f "${ROOT_DIR}/.env.example" ]]; then
    cp "${ROOT_DIR}/.env.example" "${ROOT_DIR}/.env"
    echo "Created .env from .env.example"
  else
    cat > "${ROOT_DIR}/.env" <<'EOF'
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
MOSTAQL_URL=https://mostaql.com/projects
POLL_INTERVAL=120
REQUEST_TIMEOUT=20
EOF
    echo "Created .env template"
  fi
fi

mkdir -p "${ROOT_DIR}/.state"

cat <<EOF

Setup complete.

Next steps:
1. Edit .env with your Telegram bot token and chat ID.
2. Activate the virtual environment with:
   source "${VENV_DIR}/bin/activate"
3. Run a dry check:
   python monitor.py --once --dry-run --verbose
EOF