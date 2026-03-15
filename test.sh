#!/usr/bin/env bash

set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

tests=(
  "blank|python3 fakedata_terminal.py --layout 3x2 --default-widget blank --default-colour white --text \"blank baseline\" --region-widget P2=blank --region-widget P3=blank --region-widget P4=blank --region-widget P5=blank --region-widget P6=blank --region-colour P2=bright-cyan --region-text P2='bright cyan blank' --region-colour P3=dim-white --region-text P3='dim white blank' --region-colour P4=yellow --region-text P4='yellow blank' --region-colour P5=purple --region-text P5='purple blank' --region-colour P6=black --region-text P6='black blank'"
  "blocks|python3 fakedata_terminal.py --layout 3x2 --default-widget blocks --default-speed 55 --region-widget P2=blocks --region-widget P3=blocks --region-widget P4=blocks --region-widget P5=blocks --region-widget P6=blocks --region-speed P2=20 --region-speed P3=40 --region-speed P4=70 --region-speed P5=85 --region-speed P6=100"
  "bars|python3 fakedata_terminal.py --layout 3x2 --default-widget bars --theme science --default-speed 55 --region-widget P2=bars --region-widget P3=bars --region-widget P4=bars --region-widget P5=bars --region-widget P6=bars --region-theme P2=hacker --region-speed P2=30 --region-theme P3=finance --region-speed P3=45 --region-theme P4=medicine --region-speed P4=65 --region-theme P5=navigation --region-speed P5=80 --region-theme P6=spaceteam --region-speed P6=95"
  "clock|python3 fakedata_terminal.py --layout 3x2 --default-widget clock --theme science --default-speed 55 --text 'clock baseline' --region-widget P2=clock --region-widget P3=clock --region-widget P4=clock --region-widget P5=clock --region-widget P6=clock --region-colour P2=bright-cyan --region-text P2='bright cyan' --region-direction P2=left --region-colour P3=bright-yellow --region-text P3='bright yellow' --region-direction P3=right --region-colour P4=bright-magenta --region-text P4='bright magenta' --region-direction P4=random --region-colour P5=dim-white --region-text P5='dim white' --region-direction P5=none --region-colour P6=orange --region-text P6='orange' --region-direction P6=left"
  "cycle|python3 fakedata_terminal.py --layout 3x2 --default-widget cycle --theme science --default-speed 60 --default-colour multi --region-widget P2=cycle --region-widget P3=cycle --region-widget P4=cycle --region-widget P5=cycle --region-widget P6=cycle --region-theme P2=hacker --region-speed P2=35 --region-colour P2=bright-cyan --region-theme P3=finance --region-speed P3=50 --region-colour P3=bright-yellow --region-theme P4=medicine --region-speed P4=70 --region-colour P4=bright-magenta --region-theme P5=navigation --region-speed P5=85 --region-colour P5=dim-white --region-theme P6=spaceteam --region-speed P6=95 --region-colour P6=orange"
  "image|python3 fakedata_terminal.py --layout 3x2 --default-widget image --default-speed 55 --image ${ROOT_DIR}/data/geom_33_torus.png --region-widget P2=image --region-widget P3=image --region-widget P4=image --region-widget P5=image --region-widget P6=image --region-image P2=${ROOT_DIR}/data/geom_40_geodesic_dome.png --region-speed P2=30 --region-image P3=${ROOT_DIR}/data/geom_38_prism_fan.png --region-speed P3=45 --region-image P4=${ROOT_DIR}/data/geom_14_octagon_web.png --region-speed P4=65 --region-image P5=${ROOT_DIR}/data/geom_37_interlocking_cubes.png --region-speed P5=80 --region-image P6=${ROOT_DIR}/data/geom_31_cone.png --region-speed P6=95"
  "life|python3 fakedata_terminal.py --layout 3x2 --default-widget life --default-speed 55 --region-widget P2=life --region-widget P3=life --region-widget P4=life --region-widget P5=life --region-widget P6=life --region-speed P2=20 --region-speed P3=40 --region-speed P4=60 --region-speed P5=80 --region-speed P6=100"
  "matrix|python3 fakedata_terminal.py --layout 3x2 --default-widget matrix --default-speed 55 --region-widget P2=matrix --region-widget P3=matrix --region-widget P4=matrix --region-widget P5=matrix --region-widget P6=matrix --region-speed P2=20 --region-speed P3=40 --region-speed P4=60 --region-speed P5=80 --region-speed P6=100"
  "oscilloscope|python3 fakedata_terminal.py --layout 3x2 --default-widget oscilloscope --theme science --default-speed 55 --text 'scope baseline' --region-widget P2=oscilloscope --region-widget P3=oscilloscope --region-widget P4=oscilloscope --region-widget P5=oscilloscope --region-widget P6=oscilloscope --region-theme P2=hacker --region-text P2='hacker trace' --region-direction P2=left --region-theme P3=finance --region-text P3='finance trace' --region-direction P3=right --region-theme P4=medicine --region-text P4='medicine trace' --region-direction P4=random --region-theme P5=navigation --region-text P5='nav trace' --region-direction P5=none --region-theme P6=spaceteam --region-text P6='space trace' --region-direction P6=left"
  "readouts|python3 fakedata_terminal.py --layout 3x2 --default-widget readouts --theme science --text 'readouts baseline' --default-colour white --region-widget P2=readouts --region-widget P3=readouts --region-widget P4=readouts --region-widget P5=readouts --region-widget P6=readouts --region-theme P2=hacker --region-text P2='hacker status' --region-colour P2=bright-cyan --region-theme P3=finance --region-text P3='market status' --region-colour P3=bright-yellow --region-theme P4=medicine --region-text P4='ward status' --region-colour P4=bright-magenta --region-theme P5=navigation --region-text P5='nav status' --region-colour P5=dim-white --region-theme P6=spaceteam --region-text P6='space status' --region-colour P6=orange"
  "sparkline|python3 fakedata_terminal.py --layout 3x2 --default-widget sparkline --theme science --default-speed 55 --text 'spark baseline' --region-widget P2=sparkline --region-widget P3=sparkline --region-widget P4=sparkline --region-widget P5=sparkline --region-widget P6=sparkline --region-theme P2=hacker --region-text P2='hacker spark' --region-direction P2=left --region-theme P3=finance --region-text P3='finance spark' --region-direction P3=right --region-theme P4=medicine --region-text P4='medicine spark' --region-direction P4=random --region-theme P5=navigation --region-text P5='nav spark' --region-direction P5=none --region-theme P6=spaceteam --region-text P6='space spark' --region-direction P6=left"
  "sweep|python3 fakedata_terminal.py --layout 3x2 --default-widget sweep --default-speed 55 --region-widget P2=sweep --region-widget P3=sweep --region-widget P4=sweep --region-widget P5=sweep --region-widget P6=sweep --region-speed P2=20 --region-speed P3=40 --region-speed P4=60 --region-speed P5=80 --region-speed P6=100"
  "text|python3 fakedata_terminal.py --layout 3x2 --default-widget text --theme science --default-speed 55 --text 'text baseline' --region-widget P2=text --region-widget P3=text --region-widget P4=text --region-widget P5=text --region-widget P6=text --region-theme P2=hacker --region-text P2='hacker text' --region-speed P2=30 --region-theme P3=finance --region-text P3='finance text' --region-speed P3=45 --region-theme P4=medicine --region-text P4='medicine text' --region-speed P4=65 --region-theme P5=navigation --region-text P5='nav text' --region-speed P5=80 --region-theme P6=spaceteam --region-text P6='space text' --region-speed P6=95"
  "text_scant|python3 fakedata_terminal.py --layout 3x2 --default-widget text_scant --theme science --default-speed 55 --text 'scant baseline' --region-widget P2=text_scant --region-widget P3=text_scant --region-widget P4=text_scant --region-widget P5=text_scant --region-widget P6=text_scant --region-theme P2=hacker --region-text P2='hacker scant' --region-speed P2=30 --region-theme P3=finance --region-text P3='finance scant' --region-speed P3=45 --region-theme P4=medicine --region-text P4='medicine scant' --region-speed P4=65 --region-theme P5=navigation --region-text P5='nav scant' --region-speed P5=80 --region-theme P6=spaceteam --region-text P6='space scant' --region-speed P6=95"
  "text_spew|python3 fakedata_terminal.py --layout 3x2 --default-widget text_spew --theme science --default-speed 55 --text 'spew baseline' --region-widget P2=text_spew --region-widget P3=text_spew --region-widget P4=text_spew --region-widget P5=text_spew --region-widget P6=text_spew --region-theme P2=hacker --region-text P2='hacker spew' --region-speed P2=30 --region-theme P3=finance --region-text P3='finance spew' --region-speed P3=45 --region-theme P4=medicine --region-text P4='medicine spew' --region-speed P4=65 --region-theme P5=navigation --region-text P5='nav spew' --region-speed P5=80 --region-theme P6=spaceteam --region-text P6='space spew' --region-speed P6=95"
  "text_wide|python3 fakedata_terminal.py --layout 3x2 --default-widget text_wide --theme science --default-speed 55 --text 'wide baseline' --region-widget P2=text_wide --region-widget P3=text_wide --region-widget P4=text_wide --region-widget P5=text_wide --region-widget P6=text_wide --region-theme P2=hacker --region-text P2='hacker wide' --region-speed P2=30 --region-theme P3=finance --region-text P3='finance wide' --region-speed P3=45 --region-theme P4=medicine --region-text P4='medicine wide' --region-speed P4=65 --region-theme P5=navigation --region-text P5='nav wide' --region-speed P5=80 --region-theme P6=spaceteam --region-text P6='space wide' --region-speed P6=95"
  "tunnel|python3 fakedata_terminal.py --layout 3x2 --default-widget tunnel --default-speed 55 --default-colour multi --text 'tunnel baseline' --region-widget P2=tunnel --region-widget P3=tunnel --region-widget P4=tunnel --region-widget P5=tunnel --region-widget P6=tunnel --region-colour P2=bright-cyan --region-text P2='cyan tunnel' --region-direction P2=left --region-colour P3=bright-yellow --region-text P3='yellow tunnel' --region-direction P3=right --region-colour P4=bright-magenta --region-text P4='magenta tunnel' --region-direction P4=random --region-colour P5=dim-white --region-text P5='white tunnel' --region-direction P5=none --region-colour P6=orange --region-text P6='orange tunnel' --region-direction P6=left"
)

run_test() {
  local index="$1"
  local total="$2"
  local name="$3"
  local cmd="$4"
  local status

  clear
  printf 'Test %s/%s: %s\n\n%s\n\nPress Enter to launch...' "$index" "$total" "$name" "$cmd"
  read -r

  clear
  printf 'Running test %s/%s: %s\n\n%s\n\n' "$index" "$total" "$name" "$cmd"
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
  local entry
  local name
  local cmd

  for entry in "${tests[@]}"; do
    name="${entry%%|*}"
    cmd="${entry#*|}"
    run_test "$i" "$total" "$name" "$cmd"
    i=$((i + 1))
  done

  clear
  printf 'All visual tests completed.\n'
}

main "$@"
