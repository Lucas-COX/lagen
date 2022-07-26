output "base_url" {
    description = "Base URL for API Gateway Stage"
    value = module.api_gateway.default_apigatewayv2_stage_invoke_url
}

output "function_name" {
    description = "Name of the created lambda function"
}
