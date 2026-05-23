terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../lambda/handler.py"
  output_path = "${path.module}/../lambda/lambda.zip"
}

resource "aws_dynamodb_table" "inventory" {
  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "N"
  }
}

resource "aws_iam_role" "lambda_exec" {
  name = "inventory_lambda_exec_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "inventory-lambda-policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "dynamodb:Scan",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ],
        Resource = aws_dynamodb_table.inventory.arn
      },
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_lambda_function" "inventory" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "inventory_lambda"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.9"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.inventory.name
    }
  }
}

resource "aws_api_gateway_rest_api" "inventory_api" {
  name = "inventory_api"
}

resource "aws_api_gateway_resource" "inventory_resource" {
  rest_api_id = aws_api_gateway_rest_api.inventory_api.id
  parent_id   = aws_api_gateway_rest_api.inventory_api.root_resource_id
  path_part   = "inventory"
}

resource "aws_api_gateway_method" "get_inventory" {
  rest_api_id   = aws_api_gateway_rest_api.inventory_api.id
  resource_id   = aws_api_gateway_resource.inventory_resource.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id = aws_api_gateway_rest_api.inventory_api.id
  resource_id = aws_api_gateway_resource.inventory_resource.id
  http_method = aws_api_gateway_method.get_inventory.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.inventory.invoke_arn
}

resource "aws_api_gateway_method" "post_inventory" {
  rest_api_id   = aws_api_gateway_rest_api.inventory_api.id
  resource_id   = aws_api_gateway_resource.inventory_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_integration_post" {
  rest_api_id = aws_api_gateway_rest_api.inventory_api.id
  resource_id = aws_api_gateway_resource.inventory_resource.id
  http_method = aws_api_gateway_method.post_inventory.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.inventory.invoke_arn
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.inventory.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.inventory_api.execution_arn}/*/*"
}

resource "aws_api_gateway_deployment" "inventory_deploy" {
  depends_on = [aws_api_gateway_integration.lambda_integration, aws_api_gateway_integration.lambda_integration_post]
  rest_api_id = aws_api_gateway_rest_api.inventory_api.id
  stage_name  = var.api_stage
}

output "api_invoke_url" {
  value = "${aws_api_gateway_deployment.inventory_deploy.invoke_url}/${var.api_stage}/inventory"
}
