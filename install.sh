#!/usr/bin/env bash
# Install rk, register its MCP server, and link the skills into Claude Code and Codex.
#   ./install.sh              install or update
#   ./install.sh --uninstall  remove the CLI, MCP registration and skill links (keeps your cards)
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

register_mcp() {
  local server="$1"
  if command -v claude >/dev/null 2>&1; then
    claude mcp remove --scope user rk >/dev/null 2>&1 || true
    claude mcp add --scope user rk -- "$server" >/dev/null && echo "registered MCP server in Claude Code"
  else
    echo "skip: claude not found" >&2
  fi
  if command -v codex >/dev/null 2>&1; then
    codex mcp remove rk >/dev/null 2>&1 || true
    codex mcp add rk -- "$server" >/dev/null && echo "registered MCP server in Codex"
  else
    echo "skip: codex not found" >&2
  fi
}

unregister_mcp() {
  if command -v claude >/dev/null 2>&1; then
    claude mcp remove --scope user rk >/dev/null 2>&1 && echo "removed MCP server from Claude Code" || true
  fi
  if command -v codex >/dev/null 2>&1; then
    codex mcp remove rk >/dev/null 2>&1 && echo "removed MCP server from Codex" || true
  fi
}

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

if [ "${1:-}" = "--uninstall" ]; then
  unlink_skills
  unregister_mcp
  uv tool uninstall rk || true
  echo "Your cards are still in ~/.knowledge/knowledge.db"
  exit 0
fi

uv tool install --force --editable "$REPO"
link_skills

BIN="$(uv tool dir --bin)"
register_mcp "$BIN/rk-mcp"
"$BIN/rk" init >/dev/null
echo "database ready at ${RK_DB:-$HOME/.knowledge/knowledge.db}"

if ! command -v rk >/dev/null 2>&1; then
  echo "note: $BIN is not on your PATH. Run: uv tool update-shell" >&2
fi
