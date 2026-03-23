#!/usr/bin/env bash
# setup.sh — Interactive wolfSSL repository cloner for wolfDen.
# Clones selected repos into repos/ and initializes the workspace.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPOS_DIR="$SCRIPT_DIR/repos"

# Product catalog: index name github_repo display_name
PRODUCTS=(
    "wolfssl        wolfssl/wolfssl          wolfSSL/wolfCrypt (core library)"
    "wolfssh        wolfssl/wolfssh          wolfSSH"
    "wolfmqtt       wolfssl/wolfmqtt         wolfMQTT"
    "wolftpm        wolfssl/wolfTPM          wolfTPM"
    "wolfboot       wolfssl/wolfBoot         wolfBoot"
    "wolfengine     wolfssl/wolfEngine       wolfEngine"
    "wolfprovider   wolfssl/wolfProvider     wolfProvider"
    "wolfhsm        wolfssl/wolfHSM          wolfHSM"
    "wolfclu        wolfssl/wolfClu          wolfCLU"
    "wolfssljni     wolfssl/wolfssljni       wolfSSL JNI/JSSE"
    "wolfsentry     wolfssl/wolfsentry       wolfSentry"
    "wolfpkcs11     wolfssl/wolfPKCS11       wolfPKCS11"
    "wolfguard      wolfssl/wolfGuard        wolfGuard"
    "go-wolfssl     wolfssl/go-wolfssl       go-wolfssl"
    "wolfmikey      wolfssl/wolfmikey        wolfMIKEY"
    "meta-wolfssl   wolfssl/meta-wolfssl     meta-wolfssl (Yocto/OE layer)"
    "osp            wolfssl/osp              OSP (integration patches)"
    "wolfssl-examples wolfssl/wolfssl-examples wolfSSL Examples"
    "documentation  wolfssl/documentation    wolfSSL Documentation"
    "wolfcrypt-py   wolfssl/wolfcrypt-py     wolfcrypt-py (Python wrapper)"
    "fips           wolfssl/fips-src         wolfCrypt FIPS"
    "scripts        wolfssl/scripts          Assembly Generator Scripts"
)

echo "=== wolfDen Setup ==="
echo ""
echo "This will clone wolfSSL repositories into repos/."
echo "Select which products you work on:"
echo ""

for i in "${!PRODUCTS[@]}"; do
    entry="${PRODUCTS[$i]}"
    display=$(echo "$entry" | awk '{$1=$2=""; print substr($0,3)}')
    printf "  [%2d] %s\n" $((i + 1)) "$display"
done

echo ""
echo "   [a] All products"
echo "   [q] Quit without cloning"
echo ""
read -rp "Enter numbers separated by spaces (e.g., '1 2 4'), or 'a' for all: " selection

if [ "$selection" = "q" ]; then
    echo "No repos cloned."
    exit 0
fi

# Parse selection
selected=()
if [ "$selection" = "a" ]; then
    for i in "${!PRODUCTS[@]}"; do
        selected+=("$i")
    done
else
    for num in $selection; do
        idx=$((num - 1))
        if [ "$idx" -ge 0 ] && [ "$idx" -lt "${#PRODUCTS[@]}" ]; then
            selected+=("$idx")
        else
            echo "Warning: ignoring invalid selection '$num'"
        fi
    done
fi

if [ ${#selected[@]} -eq 0 ]; then
    echo "No valid selections. Exiting."
    exit 1
fi

# Clone selected repos
mkdir -p "$REPOS_DIR"
cloned=0
skipped=0

for idx in "${selected[@]}"; do
    entry="${PRODUCTS[$idx]}"
    name=$(echo "$entry" | awk '{print $1}')
    github=$(echo "$entry" | awk '{print $2}')
    display=$(echo "$entry" | awk '{$1=$2=""; print substr($0,3)}')

    target="$REPOS_DIR/$name"
    if [ -d "$target" ]; then
        echo "  [skip] $display — already exists at repos/$name"
        skipped=$((skipped + 1))
        continue
    fi

    echo "  [clone] $display ..."
    if git clone "git@github.com:${github}.git" "$target" 2>/dev/null; then
        cloned=$((cloned + 1))
    elif git clone "https://github.com/${github}.git" "$target" 2>/dev/null; then
        echo "  (cloned via HTTPS — SSH key not configured)"
        cloned=$((cloned + 1))
    else
        echo "  [error] Failed to clone $github — check access permissions"
    fi
done

echo ""
echo "Done: $cloned cloned, $skipped already present."

# Generate initial repo state
if [ -x "$SCRIPT_DIR/.hooks/scan-repos.sh" ]; then
    echo ""
    echo "Scanning repositories..."
    bash "$SCRIPT_DIR/.hooks/scan-repos.sh"
fi

echo ""
echo "Setup complete. Run 'claude' to start working with wolfSSL domain knowledge."
