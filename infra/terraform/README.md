# Terraform

このディレクトリは、Lambda / API Gateway の実運用を Terraform で管理するための定義です。

## Scope

- Include:
  - Lambda function
  - API Gateway (REST API + Stage + Method settings)
  - Lambda 実行ロールへの SSM 読み取りポリシー付与（任意）
- Exclude:
  - DynamoDB リソース
  - IoT Core リソース

## Files

- `versions.tf`: Terraform / provider バージョン
- `provider.tf`: AWS provider
- `variables.tf`: 入力変数
- `main.tf`: Lambda / API Gateway / optional IAM policy
- `outputs.tf`: 出力値
- `terraform.tfvars.example`: 変数例
- `import_existing.sh`: 既存環境を新規 import する場合のみ利用

## Prerequisites (one-time)

1. Terraform がインストール済み
2. AWS 認証情報が利用可能
3. Terraform backend 用の専用 S3 バケットと lock 用 DynamoDB テーブル

初回セットアップ:

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
cp backend.hcl.example backend.hcl
terraform init -backend-config=backend.hcl
```

`backend.hcl` の `bucket` はこのプロジェクト専用バケットを指定します。

## Daily Operation

### 1) Lambda コードのデプロイ

```bash
./scripts/package_lambda.sh
cd infra/terraform
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

### 2) 設定値変更（runtime / timeout / memory / env / throttle）

1. `terraform.tfvars` を編集
2. `terraform plan -var-file=terraform.tfvars`
3. `terraform apply -var-file=terraform.tfvars`

### 3) LINE シークレット更新

このリポジトリでは、**SSM パラメータ本体（値）は Terraform で作成/管理しません**。
理由は、Terraform state にシークレット値を保持しないためです。

1. 必要に応じて SSM パラメータを作成（初回のみ）

```bash
aws ssm put-parameter \
  --name "/line-bot-aws-iot/prod/line-channel-secret" \
  --type SecureString \
  --value "<LINE_CHANNEL_SECRET>"

aws ssm put-parameter \
  --name "/line-bot-aws-iot/prod/line-channel-access-token" \
  --type SecureString \
  --value "<LINE_CHANNEL_ACCESS_TOKEN>"
```

2. 値の更新時は `--overwrite` 付きで実行

```bash
aws ssm put-parameter \
  --name "/line-bot-aws-iot/prod/line-channel-secret" \
  --type SecureString \
  --value "<NEW_LINE_CHANNEL_SECRET>" \
  --overwrite

aws ssm put-parameter \
  --name "/line-bot-aws-iot/prod/line-channel-access-token" \
  --type SecureString \
  --value "<NEW_LINE_CHANNEL_ACCESS_TOKEN>" \
  --overwrite
```

3. `terraform.tfvars` のパラメータ名と一致していることを確認し、`terraform plan -var-file=terraform.tfvars` で差分を確認

## GitHub Actions (Lightweight)

`.github/workflows/ci.yml` では次を実行します。

- `terraform fmt -check -recursive`
- Python の lint / format チェック（`ruff check`, `ruff format --check`）

Terraform backend や AWS 認証は不要です。
Python ジョブは必須チェックとして実行されます。

## Managed Lambda Environment

Terraform で管理する Lambda 環境変数:

- `Region`
- `ThingName`
- `TableName`
- `PartitionKey`
- `PartitionName`
- `LINE_CHANNEL_SECRET_PARAM`
- `LINE_CHANNEL_ACCESS_TOKEN_PARAM`

## Notes

- `aws_api_gateway_method_settings.throttle` は `*/*` に対して呼び出し制限を設定します。
- `enable_ssm_parameter_access = true` を維持してください。
- `line_channel_secret_param_name` と `line_channel_access_token_param_name` を空にしないでください。

## Appendix: Import Existing Environment

既存環境を新規に取り込む場合のみ使用します。

1. `terraform.tfvars` を実環境値に更新
2. `default_tags = {}` を推奨
3. 必要に応じて `manage_apigw_throttle_settings = false` で開始
4. 以下を実行

```bash
export IMPORT_LAMBDA_FUNCTION_NAME="<existing-lambda-name>"
export IMPORT_REST_API_ID="<rest-api-id>"
export IMPORT_STAGE_NAME="<stage-name>"

./import_existing.sh
terraform plan -var-file=terraform.tfvars
```
