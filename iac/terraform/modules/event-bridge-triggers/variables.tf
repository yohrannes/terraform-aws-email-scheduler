variable "cron" {
  description = "The cron expression for the downsize event"
  type        = string
}

variable "function_name" {
  description = "The name of the Lambda function."
  type        = string
  default     = null
}