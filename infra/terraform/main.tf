locals {
  lambda_role_name = element(split("/", var.lambda_role_arn), length(split("/", var.lambda_role_arn)) - 1)
  lambda_environment = merge(
    {
      Region        = var.aws_region
      ThingName     = var.iot_thing_name
      TableName     = var.dynamodb_table_name
      PartitionKey  = var.dynamodb_partition_key
      PartitionName = var.dynamodb_partition_name
    },
    var.line_channel_secret_param_name != "" ? {
      LINE_CHANNEL_SECRET_PARAM = var.line_channel_secret_param_name
    } : {},
    var.line_channel_access_token_param_name != "" ? {
      LINE_CHANNEL_ACCESS_TOKEN_PARAM = var.line_channel_access_token_param_name
    } : {}
  )
  auto_ssm_parameter_arns = compact([
    for name in [
      var.line_channel_secret_param_name,
      var.line_channel_access_token_param_name
      ] : name != "" ? format(
      "arn:%s:ssm:%s:%s:parameter%s",
      data.aws_partition.current.partition,
      var.aws_region,
      data.aws_caller_identity.current.account_id,
      startswith(name, "/") ? name : "/${name}"
    ) : ""
  ])
  effective_ssm_parameter_arns = length(var.ssm_parameter_arns) > 0 ? var.ssm_parameter_arns : local.auto_ssm_parameter_arns
}

data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

resource "aws_lambda_function" "line_bot" {
  function_name = var.lambda_function_name
  role          = var.lambda_role_arn
  runtime       = var.lambda_runtime
  handler       = var.lambda_handler
  filename      = var.lambda_zip_path

  source_code_hash = filebase64sha256(var.lambda_zip_path)
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size
  publish          = false

  environment {
    variables = local.lambda_environment
  }

  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      role,
      handler,
      publish,
      tags,
      tags_all,
    ]
  }
}

resource "aws_api_gateway_rest_api" "line_bot" {
  name = var.apigw_name

  endpoint_configuration {
    types = [var.apigw_endpoint_type]
  }

  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      endpoint_configuration,
      tags,
      tags_all,
    ]
  }
}

resource "aws_api_gateway_stage" "line_bot" {
  rest_api_id   = aws_api_gateway_rest_api.line_bot.id
  stage_name    = var.apigw_stage_name
  deployment_id = var.apigw_deployment_id

  lifecycle {
    ignore_changes = [
      deployment_id,
      tags,
      tags_all,
    ]
    prevent_destroy = true
  }
}

resource "aws_api_gateway_method_settings" "throttle" {
  count = var.manage_apigw_throttle_settings ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.line_bot.id
  stage_name  = aws_api_gateway_stage.line_bot.stage_name
  method_path = "*/*"

  settings {
    throttling_rate_limit  = var.apigw_throttle_rate_limit
    throttling_burst_limit = var.apigw_throttle_burst_limit
  }
}

resource "aws_iam_policy" "lambda_ssm_read" {
  count = var.enable_ssm_parameter_access ? 1 : 0

  name        = "${var.project_name}-lambda-ssm-read"
  description = "Allow Lambda to read SSM parameters for LINE credentials"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Effect   = "Allow"
          Action   = ["ssm:GetParameter", "ssm:GetParameters"]
          Resource = local.effective_ssm_parameter_arns
        }
      ],
      length(var.kms_key_arns_for_ssm) > 0 ? [
        {
          Effect   = "Allow"
          Action   = ["kms:Decrypt"]
          Resource = var.kms_key_arns_for_ssm
        }
      ] : []
    )
  })
}

resource "aws_iam_role_policy_attachment" "lambda_ssm_read" {
  count = var.enable_ssm_parameter_access ? 1 : 0

  role       = local.lambda_role_name
  policy_arn = aws_iam_policy.lambda_ssm_read[0].arn
}
