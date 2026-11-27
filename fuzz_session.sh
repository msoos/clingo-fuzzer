#!/bin/bash
# tmux session with one fuzz.py per window. Usage: ./fuzz_session.sh [--num N] [fuzz.py options]

SESSION="fuzzing clingo"
DIR="$(dirname "$(realpath "$0")")"
NUM_WINDOWS=$(lscpu -p=core | grep -v '^#' | sort -u | wc -l)

if [ "$1" = "--num" ]; then
  if [ -z "$2" ] || ! [[ "$2" =~ ^[0-9]+$ ]]; then
    echo "Error: --num requires a positive integer argument"
    exit 1
  fi
  NUM_WINDOWS=$2
  shift 2
fi

CMD="./fuzz.py $*"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Session '$SESSION' already exists, attaching..."
  tmux attach -t "$SESSION"
  exit 0
fi

tmux new-session -d -s "$SESSION" -c "$DIR" -n "fuzz-1"
tmux send-keys -t "$SESSION:1" "$CMD" Enter
for i in $(seq 2 "$NUM_WINDOWS"); do
  tmux new-window -t "$SESSION" -c "$DIR" -n "fuzz-$i"
  tmux send-keys -t "$SESSION:$i" "$CMD" Enter
done
tmux select-window -t "$SESSION:1"
tmux attach -t "$SESSION"
