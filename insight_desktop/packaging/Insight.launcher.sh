#!/bin/bash
# Insight.app launcher — installed as Contents/MacOS/Insight by build_app.sh.
# __REPO_ROOT__ is replaced with the absolute repo path at build time.

set -u

REPO_ROOT="__REPO_ROOT__"
MAIN_SCRIPT="$REPO_ROOT/insight_desktop/app/main.py"
VENV_CFG="$REPO_ROOT/.venv/pyvenv.cfg"
LOG_DIR="$REPO_ROOT/insight_desktop/logs"
LOG_FILE="$LOG_DIR/launcher.log"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"

mkdir -p "$LOG_DIR"

log() {
    printf '%s\n' "$@" >> "$LOG_FILE"
}

log "----- $(date) -----"

show_alert() {
    /usr/bin/osascript -e "display alert \"Insight\" message \"$1\" as critical" 2>/dev/null || true
}

# macOS privacy (TCC) often blocks GUI apps launched from Finder/Desktop from
# reading files under ~/Desktop — including .venv/pyvenv.cfg. Terminal already
# has the access users expect, so we bootstrap through it when needed.

repo_on_desktop() {
    case "$REPO_ROOT" in
        *"/Desktop"|*"/Desktop/"*) return 0 ;;
    esac
    return 1
}

can_read_repo() {
    [ -r "$VENV_CFG" ] && [ -r "$MAIN_SCRIPT" ]
}

launch_via_terminal() {
    log "Launching via Terminal (macOS Desktop privacy workaround)"
    local helper
    helper="$(mktemp "${TMPDIR:-/tmp}/insight-launch.XXXXXX.sh")"
    cat > "$helper" <<EOF
#!/bin/bash
cd $(printf '%q' "$REPO_ROOT") || exit 1
source .venv/bin/activate
exec python insight_desktop/app/main.py
EOF
    chmod +x "$helper"
    /usr/bin/osascript \
        -e 'tell application "Terminal" to activate' \
        -e "tell application \"Terminal\" to do script \"$helper\""
    return $?
}

resolve_base_python() {
    if [ ! -f "$VENV_CFG" ]; then
        return 1
    fi
    local py_home py_ver py_major py_minor python_bin site_packages
    py_home=$(grep '^home = ' "$VENV_CFG" | sed 's/^home = //')
    py_ver=$(grep '^version = ' "$VENV_CFG" | sed 's/^version = //')
    py_major=${py_ver%%.*}
    py_minor=$(echo "$py_ver" | cut -d. -f2)
    python_bin="$py_home/python${py_major}.${py_minor}"
    if [ ! -x "$python_bin" ]; then
        python_bin=$(command -v "python${py_major}.${py_minor}" 2>/dev/null || command -v python3 2>/dev/null || true)
    fi
    [ -n "$python_bin" ] && [ -x "$python_bin" ] || return 1
    site_packages="$REPO_ROOT/.venv/lib/python${py_major}.${py_minor}/site-packages"
    if [ ! -d "$site_packages" ]; then
        return 1
    fi
    export PYTHONPATH="$site_packages"
    export PYTHONNOUSERSITE=1
    export INSIGHT_REPO_ROOT="$REPO_ROOT"
    printf '%s' "$python_bin"
}

launch_direct() {
    local python_bin
    python_bin=$(resolve_base_python) || {
        if [ -x "$VENV_PYTHON" ]; then
            python_bin="$VENV_PYTHON"
        else
            log "ERROR: no Python interpreter found"
            show_alert "Python environment not found.\\n\\nRun from Terminal:\\ncd $(printf '%q' "$REPO_ROOT")\\nsource .venv/bin/activate\\npip install -r insight_desktop/requirements.txt"
            return 1
        fi
    }

    log "Direct launch: $python_bin $MAIN_SCRIPT"
    cd "$REPO_ROOT" || return 1
    exec "$python_bin" "$MAIN_SCRIPT" >> "$LOG_FILE" 2>&1
}

if [ ! -f "$MAIN_SCRIPT" ]; then
    log "ERROR: main script missing at $MAIN_SCRIPT"
    show_alert "Insight project files not found at:\\n$REPO_ROOT\\n\\nRebuild the app after moving the project:\\nbash insight_desktop/packaging/build_app.sh"
    exit 1
fi

if repo_on_desktop || ! can_read_repo; then
    log "Using Terminal bootstrap (repo_on_desktop=$(repo_on_desktop && echo yes || echo no), can_read=$(can_read_repo && echo yes || echo no))"
    launch_via_terminal >> "$LOG_FILE" 2>&1
    exit $?
fi

launch_direct
status=$?
if [ "$status" -ne 0 ]; then
    log "Direct launch failed with status $status — retrying via Terminal"
    launch_via_terminal >> "$LOG_FILE" 2>&1
    exit $?
fi

exit "$status"
