variable "aws_region" {
  description = "AWS region where resources are deployed"
  type        = string
}

variable "project_name" {
  description = "Project tag value"
  type        = string
  default     = "line-bot-aws-iot"
}

variable "environment" {
  description = "Environment tag value"
  type        = string
  default     = "prod"
}

variable "default_tags" {
  description = "Default AWS tags to apply. Keep empty during initial import for zero-drift."
  type        = map(string)
  default     = {}
}

variable "lambda_function_name" {
  description = "Existing Lambda function name"
  type        = string
}

variable "lambda_role_arn" {
  description = "IAM role ARN used by Lambda"
  type        = string
}

variable "lambda_runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.12"
}

variable "lambda_handler" {
  description = "Lambda handler entrypoint"
  type        = string
  default     = "src.lambda_handler.lambda_handler"
}

variable "lambda_timeout" {
  description = "Lambda timeout seconds"
  type        = number
  default     = 10
}

variable "lambda_memory_size" {
  description = "Lambda memory size MB"
  type        = number
  default     = 128
}

variable "iot_thing_name" {
  description = "AWS IoT thing name used by the Lambda"
  type        = string
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name used by the Lambda"
  type        = string
}

variable "dynamodb_partition_key" {
  description = "Partition key attribute name for the DynamoDB lookup"
  type        = string
}

variable "dynamodb_partition_name" {
  description = "Partition key value used for the DynamoDB lookup"
  type        = string
}

variable "lambda_zip_path" {
  description = "Path to Lambda deployment zip"
  type        = string
  default     = "../../dist/line-bot-aws-iot-lambda.zip"
}

variable "apigw_name" {
  description = "Existing API Gateway REST API name"
  type        = string
}

variable "apigw_stage_name" {
  description = "Existing API Gateway stage name"
  type        = string
}

variable "apigw_deployment_id" {
  description = "Current API Gateway deployment ID"
  type        = string
}

variable "apigw_endpoint_type" {
  description = "API Gateway endpoint type"
  type        = string
  default     = "EDGE"
}

variable "manage_apigw_throttle_settings" {
  description = "Manage API Gateway stage-wide throttle settings"
  type        = bool
  default     = false
}

variable "apigw_throttle_rate_limit" {
  description = "API Gateway stage throttle rate limit"
  type        = number
  default     = 5
}

variable "apigw_throttle_burst_limit" {
  description = "API Gateway stage throttle burst limit"
  type        = number
  default     = 10
}

variable "enable_ssm_parameter_access" {
  description = "Attach SSM read policy to Lambda role"
  type        = bool
  default     = false
}

variable "line_channel_secret_param_name" {
  description = "SSM parameter name for LINE channel secret"
  type        = string
  default     = ""
}

variable "line_channel_access_token_param_name" {
  description = "SSM parameter name for LINE channel access token"
  type        = string
  default     = ""
}

variable "ssm_parameter_arns" {
  description = "Allowed SSM parameter ARNs for Lambda"
  type        = list(string)
  default     = []
}

variable "kms_key_arns_for_ssm" {
  description = "KMS CMK ARNs used to decrypt SecureString parameters"
  type        = list(string)
  default     = []
}
