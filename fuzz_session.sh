#!/bin/bash
# tmux session with one fuzz.py per window, a third of them on big programs. Usage: ./fuzz_session.sh [--num N] [fuzz.py options]

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
BIG_CMD="./fuzz.py --size big --tout 10 $*"
NUM_BIG=$((NUM_WINDOWS / 3))
[[ " $* " == *" --size"* ]] && NUM_BIG=0

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Session '$SESSION' already exists, attaching..."
  tmux attach -t "$SESSION"
  exit 0
fi

for i in $(seq 1 "$NUM_WINDOWS"); do
  if [ "$i" -le "$NUM_BIG" ]; then c="$BIG_CMD"; n="big-$i"; else c="$CMD"; n="fuzz-$i"; fi
  if [ "$i" = 1 ]; then tmux new-session -d -s "$SESSION" -c "$DIR" -n "$n"
  else                  tmux new-window -t "$SESSION" -c "$DIR" -n "$n"; fi
  tmux send-keys -t "$SESSION:$i" "$c" Enter
done
tmux select-window -t "$SESSION:1"
tmux attach -t "$SESSION"
