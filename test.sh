#!/usr/bin/env bash

set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

tests=(
  "python3 app.py --style test1"
  "python3 app.py --style geometries --panel-colour full=multi"
  "python3 app.py --style tunnel --panel-speed full=90"
  "python3 app.py --layout grid_2x2 --vocab science --assign p1=text_wide --assign p2=readouts --assign p3=matrix --assign p4=clock"
  "python3 app.py --layout grid_3x3 --vocab hacker --assign large_left=cycle --assign right=readouts --panel-colour large_left=multi --panel-speed right=80"
  "python3 app.py --layout main_2x2_right_stack_3 --vocab pharmacy --assign main=text --assign right_top=bars --assign right_mid=sparkline --assign right_bottom=life --text \"VERIFY RX QUEUE\""
  "python3 app.py --layout left_stack_2_right_grid_3x3 --vocab science --assign left=image --assign right_center=tunnel --assign right_right=clock --panel-image left=${ROOT_DIR}/data/geom_33_torus.png --panel-image left=${ROOT_DIR}/data/geom_40_geodesic_dome.png"
  "python3 app.py --layout grid_3x2 --vocab navigation --assign main=sweep --assign right_top=readouts --assign right_bottom=blocks --glitch 4"
  "python3 app.py --demo"
)

run_test() {
  local index="$1"
  local total="$2"
  local cmd="$3"
  local status

  clear
  printf 'Test %s/%s\n\n%s\n\nPress Enter to launch...' "$index" "$total" "$cmd"
  read -r

  clear
  printf 'Running test %s/%s\n\n%s\n\n' "$index" "$total" "$cmd"
  (
    cd "$ROOT_DIR" || exit 1
    bash -lc "$cmd"
  )
  status=$?

  printf '\nExit status: %s\nPress Enter to continue...' "$status"
  read -r
}

main() {
  local total="${#tests[@]}"
  local i=1

  for cmd in "${tests[@]}"; do
    run_test "$i" "$total" "$cmd"
    i=$((i + 1))
  done

  clear
  printf 'All visual tests completed.\n'
}

main "$@"
