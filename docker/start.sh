#!/usr/bin/env bash
set -euo pipefail

capture_args=(
    -r -
    -f "${HACKRF_FREQUENCY_HZ:-1090000000}"
    -s 8000000
    -b 1750000
    -a "${HACKRF_AMP_ENABLE:-0}"
    -l "${HACKRF_LNA_GAIN:-16}"
    -g "${HACKRF_VGA_GAIN:-20}"
)

if [[ -n "${HACKRF_SERIAL:-}" ]]; then
    capture_args+=(-d "$HACKRF_SERIAL")
fi

echo 'Capturing HackRF IQ at 8 MS/s; recording CS8 segments and decoding at 2 MS/s.' >&2

hackrf_transfer "${capture_args[@]}" \
    | python3 /app/docker/record.py \
    | ffmpeg -nostdin -hide_banner -loglevel error \
        -f s8 -ar 8000000 -ac 2 -i pipe:0 \
        -ar 2000000 -ac 2 -f u8 pipe:1 \
    | /app/dump1090 --ifile - --net
