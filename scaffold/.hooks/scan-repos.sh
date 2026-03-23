#!/usr/bin/env bash
# scan-repos.sh — Detects wolfSSL repos in repos/ and generates context for Claude.
# Runs as a SessionStart hook. Output goes directly into Claude's context.
# Compatible with bash 3.2+ (macOS default).
set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPOS_DIR="$WORKSPACE_DIR/repos"
STATE_FILE="$WORKSPACE_DIR/.wolfssl-repos-state.json"
CONTEXT_FILE="$WORKSPACE_DIR/.repos-context.md"

# Product display name lookup (bash 3.x compatible — no associative arrays)
get_display_name() {
    case "$1" in
        wolfssl)          echo "wolfSSL/wolfCrypt" ;;
        wolfssh)          echo "wolfSSH" ;;
        wolfmqtt)         echo "wolfMQTT" ;;
        wolfboot)         echo "wolfBoot" ;;
        wolftpm)          echo "wolfTPM" ;;
        wolfengine)       echo "wolfEngine" ;;
        wolfprovider)     echo "wolfProvider" ;;
        wolfhsm)          echo "wolfHSM" ;;
        wolfclu)          echo "wolfCLU" ;;
        wolfssljni)       echo "wolfSSL JNI/JSSE" ;;
        wolfsentry)       echo "wolfSentry" ;;
        wolfpkcs11)       echo "wolfPKCS11" ;;
        wolfcrypt-py)     echo "wolfcrypt-py" ;;
        wolfguard)        echo "wolfGuard" ;;
        go-wolfssl)       echo "go-wolfssl" ;;
        wolfmikey)        echo "wolfMIKEY" ;;
        meta-wolfssl)     echo "meta-wolfssl (Yocto)" ;;
        osp)              echo "OSP (integration patches)" ;;
        wolfssl-examples) echo "wolfSSL Examples" ;;
        documentation)    echo "wolfSSL Documentation" ;;
        scripts)          echo "Assembly Generator Scripts" ;;
        fips)             echo "wolfCrypt FIPS" ;;
        *)                echo "$1" ;;
    esac
}

if [ ! -d "$REPOS_DIR" ]; then
    echo "No repos/ directory found. Run ./setup.sh to clone wolfSSL repositories."
    exit 0
fi

# Discover git repos
repos_found=""
repo_count=0
repo_data=""

for dir in "$REPOS_DIR"/*/; do
    [ -d "$dir/.git" ] || continue
    name=$(basename "$dir")
    repos_found="$repos_found $name"
    repo_count=$((repo_count + 1))

    # Get branch and short commit
    branch=$(git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    commit=$(git -C "$dir" rev-parse --short HEAD 2>/dev/null || echo "unknown")
    display_name=$(get_display_name "$name")

    repo_data="${repo_data}| ${display_name} | repos/${name} | ${branch} | ${commit} |
"
done

if [ "$repo_count" -eq 0 ]; then
    echo "repos/ directory exists but contains no git repositories. Run ./setup.sh or clone repos manually into repos/."
    exit 0
fi

# Build new state (simple JSON)
new_state="{"
first=true
for name in $repos_found; do
    dir="$REPOS_DIR/$name"
    commit=$(git -C "$dir" rev-parse HEAD 2>/dev/null || echo "unknown")
    branch=$(git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    if $first; then
        first=false
    else
        new_state="${new_state},"
    fi
    new_state="${new_state}\"${name}\":{\"commit\":\"${commit}\",\"branch\":\"${branch}\"}"
done
new_state="${new_state}}"

# Check if state changed
state_changed=true
if [ -f "$STATE_FILE" ]; then
    old_state=$(cat "$STATE_FILE")
    if [ "$old_state" = "$new_state" ] && [ -f "$CONTEXT_FILE" ]; then
        state_changed=false
    fi
fi

# Update state and context if changed
if $state_changed; then
    echo "$new_state" > "$STATE_FILE"

    cat > "$CONTEXT_FILE" <<CTXEOF
## Active Repositories

| Product | Path | Branch | Commit |
|---------|------|--------|--------|
${repo_data}
Use these paths when searching, reading, or navigating code.
CTXEOF
fi

# Always output summary for Claude's session context
echo "Workspace has ${repo_count} wolfSSL repo(s):"
for name in $repos_found; do
    dir="$REPOS_DIR/$name"
    display_name=$(get_display_name "$name")
    branch=$(git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
    commit=$(git -C "$dir" rev-parse --short HEAD 2>/dev/null || echo "?")
    echo "  - $display_name (repos/$name, $branch@$commit)"
done
