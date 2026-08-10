module "event_bridge_triggers" {
  source        = "./modules/event-bridge-triggers"
  cron          = var.function_cron
  function_name = var.function_name
}

module "iam_roles" {
  source        = "./modules/iam_roles"
  aws_region    = var.aws_region
  function_name = var.function_name
}