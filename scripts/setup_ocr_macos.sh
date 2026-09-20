#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  printf 'This helper is for macOS. Install Tesseract with eng and chi_sim language data on this host.\n' >&2
  exit 1
fi
if ! command -v brew >/dev/null 2>&1; then
  printf 'Homebrew is required for this helper.\n' >&2
  exit 1
fi
if ! command -v tesseract >/dev/null 2>&1; then
  brew install tesseract
fi
if tesseract --list-langs 2>&1 | grep -qx 'chi_sim'; then
  printf 'Chinese OCR data is already installed.\n'
  exit 0
fi

tessdata_dir="$(brew --prefix tesseract)/share/tessdata"
expected_sha='a5fcb6f0db1e1d6d8522f39db4e848f05984669172e584e8d76b6b3141e1f730'
scratch_file="$(mktemp)"
trap 'rm -f "$scratch_file"' EXIT
curl --fail --location --silent --show-error \
  'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/chi_sim.traineddata' \
  --output "$scratch_file"
actual_sha="$(shasum -a 256 "$scratch_file" | awk '{print $1}')"
if [[ "$actual_sha" != "$expected_sha" ]]; then
  printf 'OCR language file checksum changed. Installation stopped.\n' >&2
  exit 1
fi
install -m 0644 "$scratch_file" "$tessdata_dir/chi_sim.traineddata"
printf 'Installed chi_sim OCR language data from tesseract-ocr/tessdata_fast.\n'
