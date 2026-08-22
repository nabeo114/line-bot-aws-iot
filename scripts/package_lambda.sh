#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build/lambda"
DIST_DIR="$ROOT_DIR/dist"
ARTIFACT_NAME="line-bot-aws-iot-lambda.zip"
ARTIFACT_PATH="$DIST_DIR/$ARTIFACT_NAME"

if ! command -v zip >/dev/null 2>&1; then
  echo "Error: zip command is required but not installed." >&2
  exit 1
fi

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR" "$DIST_DIR"

cp -R "$ROOT_DIR/src" "$BUILD_DIR/src"

find "$BUILD_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$BUILD_DIR" -type f -name "*.pyc" -delete

rm -f "$ARTIFACT_PATH"
(
  cd "$BUILD_DIR"
  zip -rq "$ARTIFACT_PATH" src
)

echo "Created: $ARTIFACT_PATH"
