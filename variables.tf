## AWS provider configuration variables.

variable "aws_region" {
  description = "The AWS region where resources are deployed."
  type        = string
  default     = ""
}

variable "aws_profile" {
  description = "The AWS profile to use for authentication."
  type        = string
  default     = ""
}

variable "function_name" {
  description = "The name of the Lambda function."
  type        = string
  default     = ""
}

variable "function_cron" {
  description = "The cron expression for the Lambda function."
  type        = string
  default     = ""
}

variable "subnet-id" {
  description = "The id of subnet"
  type = string
  default = ""
}

variable "security-group-id" {
  description = "The id of security group"
  type = string
  default = ""
}

variable "google_token_json" {
  description = "The Google OAuth token JSON string."
  type        = string
  sensitive   = true
}

variable "destination_email" {
  description = "The recipient email address for Gmail notifications."
  type        = string
}

variable "image_bucket" {
  description = "The S3 bucket containing the images."
  type        = string
}

variable "image_prefix" {
  description = "The S3 directory prefix for the images."
  type        = string
  default     = ""
}

variable "image_index_ssm_param" {
  description = "The SSM parameter name to store the current image index."
  type        = string
}

variable "email_body_text" {
  description = "The static body text for the email."
  type        = string
  default     = ""
}
