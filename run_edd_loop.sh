#!/bin/bash
# Continuous EDD loop - runs overnight autonomously
# Each iteration picks a new candidate PR, evaluates it, and moves on

cd "$(dirname "$0")"

LOG="$(pwd)/edd-overnight.log"
PYTHON="${PYTHON:-python3}"

echo "========================================" >> "$LOG"
echo "EDD overnight loop started: $(date -u)" >> "$LOG"
echo "========================================" >> "$LOG"

ITERATION=0
MAX_ITERATIONS=20  # Safety cap

while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    ITERATION=$((ITERATION + 1))
    echo "" >> "$LOG"
    echo "--- Iteration $ITERATION started: $(date -u) ---" >> "$LOG"
    
    # Check eval server health
    HEALTH=$(curl -s http://localhost:8200/health 2>/dev/null)
    if [ "$HEALTH" != '{"status":"ok"}' ]; then
        echo "Eval server not healthy, restarting..." >> "$LOG"
        pkill -f "scripts.edd.eval_server" 2>/dev/null
        sleep 2
        nohup $PYTHON -m scripts.edd.eval_server >> /tmp/edd-eval-server.log 2>&1 &
        sleep 3
        HEALTH=$(curl -s http://localhost:8200/health 2>/dev/null)
        if [ "$HEALTH" != '{"status":"ok"}' ]; then
            echo "FATAL: Could not restart eval server. Exiting." >> "$LOG"
            exit 1
        fi
        echo "Eval server restarted successfully" >> "$LOG"
    fi
    
    # Run EDD loop - auto-selects a new candidate PR
    echo "Running EDD auto-select (iteration $ITERATION)..." >> "$LOG"
    $PYTHON -m scripts.edd --iterations 1 --limit 30 >> "$LOG" 2>&1
    EXIT_CODE=$?
    
    echo "EDD exited with code $EXIT_CODE at $(date -u)" >> "$LOG"
    
    if [ $EXIT_CODE -ne 0 ]; then
        echo "WARNING: EDD exited with error, continuing to next iteration..." >> "$LOG"
    fi
    
    # Brief pause between iterations
    sleep 10
done

echo "" >> "$LOG"
echo "========================================" >> "$LOG"
echo "EDD overnight loop finished: $(date -u)" >> "$LOG"
echo "Completed $ITERATION iterations" >> "$LOG"
echo "========================================" >> "$LOG"
