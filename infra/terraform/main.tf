locals {
  lambda_role_name = var.lambda_role_name
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
  lambda_iot_thing_arn = format(
    "arn:%s:iot:%s:%s:thing/%s",
    data.aws_partition.current.partition,
    var.aws_region,
    data.aws_caller_identity.current.account_id,
    var.iot_thing_name
  )
  lambda_dynamodb_table_arn = format(
    "arn:%s:dynamodb:%s:%s:table/%s",
    data.aws_partition.current.partition,
    var.aws_region,
    data.aws_caller_identity.current.account_id,
    var.dynamodb_table_name
  )
  active_lambda_function_arn  = aws_lambda_function.line_bot.arn
  active_lambda_function_name = aws_lambda_function.line_bot.function_name
}

moved {
  from = aws_lambda_function.line_bot_new[0]
  to   = aws_lambda_function.line_bot
}

data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

resource "aws_iam_role" "lambda_exec" {
  name        = local.lambda_role_name
  path        = "/"
  description = "Allows Lambda functions to call AWS services on your behalf."
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
  max_session_duration = 3600

  lifecycle {
    ignore_changes = [
      tags,
      tags_all,
    ]
  }
}

resource "aws_lambda_function" "line_bot" {
  function_name = var.lambda_function_name
  role          = aws_iam_role.lambda_exec.arn
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
    ignore_changes = [
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

resource "aws_api_gateway_method" "linebot_post" {
  count = var.manage_apigw_linebot_post ? 1 : 0

  rest_api_id      = aws_api_gateway_rest_api.line_bot.id
  resource_id      = var.apigw_linebot_resource_id
  http_method      = var.apigw_linebot_http_method
  authorization    = "NONE"
  api_key_required = false

  request_validator_id = var.apigw_linebot_request_validator_id != "" ? var.apigw_linebot_request_validator_id : null
  request_parameters   = var.apigw_linebot_request_parameters

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_api_gateway_integration" "linebot_post" {
  count = var.manage_apigw_linebot_post ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.line_bot.id
  resource_id = aws_api_gateway_method.linebot_post[0].resource_id
  http_method = aws_api_gateway_method.linebot_post[0].http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = format("arn:%s:apigateway:%s:lambda:path/2015-03-31/functions/%s/invocations", data.aws_partition.current.partition, var.aws_region, local.active_lambda_function_arn)
  passthrough_behavior    = "WHEN_NO_MATCH"
  content_handling        = "CONVERT_TO_TEXT"
  timeout_milliseconds    = 29000

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_lambda_permission" "apigw_invoke_linebot_post" {
  count = var.manage_apigw_linebot_post ? 1 : 0

  statement_id  = var.apigw_invoke_permission_statement_id
  action        = "lambda:InvokeFunction"
  function_name = local.active_lambda_function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = format(
    "%s/*/%s/%s",
    aws_api_gateway_rest_api.line_bot.execution_arn,
    var.apigw_linebot_http_method,
    var.apigw_linebot_resource_path
  )
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

resource "aws_iam_policy" "lambda_device_access" {
  name        = "${var.project_name}-lambda-device-access"
  description = "Least-privilege access for IoT shadow and DynamoDB item reads"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["iot:GetThingShadow", "iot:UpdateThingShadow"]
        Resource = local.lambda_iot_thing_arn
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem"]
        Resource = local.lambda_dynamodb_table_arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = local.lambda_role_name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_device_access" {
  role       = local.lambda_role_name
  policy_arn = aws_iam_policy.lambda_device_access.arn
}
