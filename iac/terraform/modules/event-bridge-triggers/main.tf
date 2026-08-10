resource "aws_cloudwatch_event_rule" "cron_trigger" {
  name                = "cron_trigger_${var.function_name}_rule"
  description         = "cron_trigger_rule"
  schedule_expression = "cron(${var.cron})"
}