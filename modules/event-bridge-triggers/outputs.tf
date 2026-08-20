output "cron_trigger_name" {
  value = aws_cloudwatch_event_rule.cron_trigger.name
}
output "cron_trigger_arn" {
  value = aws_cloudwatch_event_rule.cron_trigger.arn
}