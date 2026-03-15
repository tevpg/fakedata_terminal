#!/usr/bin/env bash

set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

tests=(
  "python3 fakedata_terminal.py --scene test1"
  "python3 fakedata_terminal.py --scene geometries --region-colour full=multi"
  "python3 fakedata_terminal.py --scene tunnel --region-speed full=90"
  "python3 fakedata_terminal.py --layout 3x3 --default-widget cycle --default-speed 70 --default-colour cyan --region-widget L2=image --region-image L2=${ROOT_DIR}/data/geom_33_torus.png"
  "python3 fakedata_terminal.py --layout 2x2 --theme science --region-widget P1=text_wide --region-widget P2=readouts --region-widget P3=matrix --region-widget P4=clock"
  "python3 fakedata_terminal.py --layout 3x3 --theme hacker --region-widget L2=cycle --region-widget R=readouts --region-colour L2=multi --region-speed R=80"
  "python3 fakedata_terminal.py --layout L2x2_R3 --theme pharmacy --region-widget L2x2=text --region-widget P5=bars --region-widget P6=sparkline --region-widget P7=life --text \"VERIFY RX QUEUE\""
  "python3 fakedata_terminal.py --layout L2_R3x3 --theme science --region-widget L=image --region-widget RC=tunnel --region-widget R2=clock --region-image L=${ROOT_DIR}/data/geom_33_torus.png --region-image L=${ROOT_DIR}/data/geom_40_geodesic_dome.png"
  "python3 fakedata_terminal.py --layout 3x2 --theme navigation --region-widget L2x2=sweep --region-widget P5=readouts --region-widget P6=blocks --glitch 4"
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
