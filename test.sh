#!/usr/bin/env bash

set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

tests=(
  "python3 fakedata_terminal.py --scene test1"
  "python3 fakedata_terminal.py --scene geometries --panel-colour full=multi"
  "python3 fakedata_terminal.py --scene tunnel --panel-speed full=90"
  "python3 fakedata_terminal.py --layout grid_3x3 --default-widget cycle --default-speed 70 --default-colour cyan --panel-widget large_left=image --panel-image large_left=${ROOT_DIR}/data/geom_33_torus.png"
  "python3 fakedata_terminal.py --layout grid_2x2 --vocab science --panel-widget p1=text_wide --panel-widget p2=readouts --panel-widget p3=matrix --panel-widget p4=clock"
  "python3 fakedata_terminal.py --layout grid_3x3 --vocab hacker --panel-widget large_left=cycle --panel-widget right=readouts --panel-colour large_left=multi --panel-speed right=80"
  "python3 fakedata_terminal.py --layout main_2x2_right_stack_3 --vocab pharmacy --panel-widget main=text --panel-widget right_top=bars --panel-widget right_mid=sparkline --panel-widget right_bottom=life --text \"VERIFY RX QUEUE\""
  "python3 fakedata_terminal.py --layout left_stack_2_right_grid_3x3 --vocab science --panel-widget left=image --panel-widget right_center=tunnel --panel-widget right_right=clock --panel-image left=${ROOT_DIR}/data/geom_33_torus.png --panel-image left=${ROOT_DIR}/data/geom_40_geodesic_dome.png"
  "python3 fakedata_terminal.py --layout grid_3x2 --vocab navigation --panel-widget main=sweep --panel-widget right_top=readouts --panel-widget right_bottom=blocks --glitch 4"
  "python3 fakedata_terminal.py --demo"
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
