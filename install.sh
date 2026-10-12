#!/usr/bin/env bash
# Install rk and link the skills into Claude Code and Codex.
#   ./install.sh              install or update
#   ./install.sh --uninstall  remove the CLI and skill links (keeps your cards)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS=(save-knowledge recall-knowledge)
TARGETS=("$HOME/.claude/skills" "${CODEX_HOME:-$HOME/.codex}/skills")

link_skills() {
  for dir in "${TARGETS[@]}"; do
    mkdir -p "$dir"
    for skill in "${SKILLS[@]}"; do
      dest="$dir/$skill"
      src="$REPO/skills/$skill"
      if [ -L "$dest" ]; then
        ln -sfn "$src" "$dest"
      elif [ -e "$dest" ]; then
        echo "skip: $dest exists and is not a symlink" >&2
        continue
      else
        ln -s "$src" "$dest"
      fi
      echo "linked $dest"
    done
  done
}

unlink_skills() {
  for dir in "${TARGETS[@]}"; do
    for skill in "${SKILLS[@]}"; do
      dest="$dir/$skill"
      if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$REPO/skills/$skill" ]; then
        rm "$dest" && echo "removed $dest"
      fi
    done
  done
}

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

if [ "${1:-}" = "--uninstall" ]; then
  unlink_skills
  uv tool uninstall rk || true
  echo "Your cards are still in ~/.knowledge/knowledge.db"
  exit 0
fi

uv tool install --force --editable "$REPO"
link_skills

RK="$(uv tool dir --bin)/rk"
"$RK" init >/dev/null
echo "database ready at ${RK_DB:-$HOME/.knowledge/knowledge.db}"

if ! command -v rk >/dev/null 2>&1; then
  echo "note: $(uv tool dir --bin) is not on your PATH. Run: uv tool update-shell" >&2
fi

cat <<EOF

Codex runs commands in a sandbox that cannot write to ~/.knowledge by default.
To let /save-knowledge and /recall-knowledge work without approval prompts, add
this to ${CODEX_HOME:-$HOME/.codex}/config.toml:

  [sandbox_workspace_write]
  writable_roots = ["$HOME/.knowledge"]
EOF
