variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "dynamodb_table_name" {
  type    = string
  default = "inventory"
}

variable "api_stage" {
  type    = string
  default = "prod"
}
