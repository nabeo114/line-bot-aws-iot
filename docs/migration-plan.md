# Modernization Status

## Completed

- Repository layout cleanup (`src/`, `assets/images/`, `infra/terraform/`)
- Lambda / API Gateway import into Terraform
- Terraform remote state on S3 + DynamoDB lock
- LINE secret migration to SSM Parameter Store
- Lambda environment/runtime/timeout/memory managed by Terraform
- API Gateway throttling managed by Terraform
- Lambda code deployment managed by Terraform (`filename` / `source_code_hash`)

## Remaining High-Priority Tasks

1. GitHub Actions で `terraform plan` まで自動化
2. 監視設定の追加

## Monitoring Backlog (recommended)

- CloudWatch Logs の保持期間を Terraform で明示管理
- Lambda エラー率 / Duration / Throttle のアラーム追加
- API Gateway 4xx / 5xx / Latency のアラーム追加
