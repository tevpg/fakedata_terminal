#!/usr/bin/env bash

set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

tests=(
  "python3 fakedata_terminal.py --scene test1"
  "python3 fakedata_terminal.py --scene geometries --panel-colour full=multi"
  "python3 fakedata_terminal.py --scene tunnel --panel-speed full=90"
  "python3 fakedata_terminal.py --layout 3x3 --default-widget cycle --default-speed 70 --default-colour cyan --panel-widget L2=image --panel-image L2=${ROOT_DIR}/data/geom_33_torus.png"
  "python3 fakedata_terminal.py --layout 2x2 --theme science --panel-widget P1=text_wide --panel-widget P2=readouts --panel-widget P3=matrix --panel-widget P4=clock"
  "python3 fakedata_terminal.py --layout 3x3 --theme hacker --panel-widget L2=cycle --panel-widget R=readouts --panel-colour L2=multi --panel-speed R=80"
  "python3 fakedata_terminal.py --layout L2x2_R3 --theme pharmacy --panel-widget L2x2=text --panel-widget P5=bars --panel-widget P6=sparkline --panel-widget P7=life --text \"VERIFY RX QUEUE\""
  "python3 fakedata_terminal.py --layout L2_R3x3 --theme science --panel-widget L=image --panel-widget RC=tunnel --panel-widget R2=clock --panel-image L=${ROOT_DIR}/data/geom_33_torus.png --panel-image L=${ROOT_DIR}/data/geom_40_geodesic_dome.png"
  "python3 fakedata_terminal.py --layout 3x2 --theme navigation --panel-widget L2x2=sweep --panel-widget P5=readouts --panel-widget P6=blocks --glitch 4"
  "python3 fakedata_terminal.py --scenes"
  "python3 fakedata_terminal.py --widgets"
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
