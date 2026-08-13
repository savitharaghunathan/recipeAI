#!/usr/bin/env bash
# Ensure OPENAI_API_KEY is available (env, .env, or interactive prompt).
# Writes .env when prompting so later runs reuse it.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"

load_dotenv() {
  [[ -f "$ENV_FILE" ]] || return 0
  # shellcheck disable=SC1090
  set -a
  # Only export simple KEY=VALUE lines (ignore comments/blank)
  # shellcheck disable=SC2046
  export $(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$ENV_FILE" | xargs) 2>/dev/null || true
  set +a
}

load_dotenv

if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is set (${#OPENAI_API_KEY} chars)"
  # Keep .env in sync when key came from the environment
  if [[ ! -f "$ENV_FILE" ]] || ! grep -q '^OPENAI_API_KEY=' "$ENV_FILE" 2>/dev/null; then
    umask 077
    printf 'OPENAI_API_KEY=%s\n' "$OPENAI_API_KEY" >"$ENV_FILE"
    echo "Wrote $ENV_FILE"
  fi
  exit 0
fi

if [[ ! -t 0 ]]; then
  echo "error: OPENAI_API_KEY is not set and no TTY for prompting." >&2
  echo "  export OPENAI_API_KEY=sk-...  or create $ENV_FILE" >&2
  exit 1
fi

echo "No OPENAI_API_KEY found. Create one at https://platform.openai.com/api-keys"
printf "Paste your OpenAI API key: "
# -s hides input; still works in most terminals
read -rs KEY
echo
[[ -n "$KEY" ]] || { echo "error: empty key" >&2; exit 1; }

umask 077
if [[ -f "$ENV_FILE" ]]; then
  if grep -q '^OPENAI_API_KEY=' "$ENV_FILE"; then
    # Replace existing line (portable: rewrite file)
    grep -v '^OPENAI_API_KEY=' "$ENV_FILE" >"${ENV_FILE}.tmp" || true
    printf 'OPENAI_API_KEY=%s\n' "$KEY" >>"${ENV_FILE}.tmp"
    mv "${ENV_FILE}.tmp" "$ENV_FILE"
  else
    printf '\nOPENAI_API_KEY=%s\n' "$KEY" >>"$ENV_FILE"
  fi
else
  printf 'OPENAI_API_KEY=%s\n' "$KEY" >"$ENV_FILE"
fi
chmod 600 "$ENV_FILE"
export OPENAI_API_KEY="$KEY"
echo "Saved OPENAI_API_KEY to $ENV_FILE"
