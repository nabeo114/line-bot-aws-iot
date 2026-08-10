#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v terraform >/dev/null 2>&1; then
  echo "Error: terraform command is required." >&2
  exit 1
fi

: "${IMPORT_LAMBDA_FUNCTION_NAME:?Set IMPORT_LAMBDA_FUNCTION_NAME}"
: "${IMPORT_REST_API_ID:?Set IMPORT_REST_API_ID}"
: "${IMPORT_STAGE_NAME:?Set IMPORT_STAGE_NAME}"

cd "$SCRIPT_DIR"

terraform init

terraform import aws_lambda_function.line_bot "$IMPORT_LAMBDA_FUNCTION_NAME"
terraform import aws_api_gateway_rest_api.line_bot "$IMPORT_REST_API_ID"
terraform import aws_api_gateway_stage.line_bot "$IMPORT_REST_API_ID/$IMPORT_STAGE_NAME"
terraform import aws_api_gateway_method_settings.throttle "$IMPORT_REST_API_ID/$IMPORT_STAGE_NAME/*/*"

echo "Import complete. Next step: terraform plan -var-file=terraform.tfvars"
