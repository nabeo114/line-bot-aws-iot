output "lambda_function_name" {
  value = aws_lambda_function.line_bot.function_name
}

output "api_gateway_rest_api_id" {
  value = aws_api_gateway_rest_api.line_bot.id
}

output "api_gateway_stage_name" {
  value = aws_api_gateway_stage.line_bot.stage_name
}
