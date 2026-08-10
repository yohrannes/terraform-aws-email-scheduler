variable "aws_region" {
  description = "The AWS region to be used in the policy"
  type        = string
}

variable "function_name" {
  description = "The name of the Lambda function."
  type        = string
  default     = null
}