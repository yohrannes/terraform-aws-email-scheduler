resource "aws_lambda_layer_version" "python_dependencies" {
  filename   = "${path.module}/lambda-layers/python-dependencies.zip"
  layer_name = "python-dependencies"

  compatible_runtimes = ["python3.12"]

  depends_on = [null_resource.create_lambda_layer]
}

resource "null_resource" "create_lambda_layer" {
  provisioner "local-exec" {
    command = <<-EOT
      mkdir -p ${path.module}/lambda-layers/python
      pip install -r ${path.module}/lambda-layers/requirements.txt -t ${path.module}/lambda-layers/python/
      find ${path.module}/lambda-layers/python/ -type d -name "__pycache__" -exec rm -rf {} +
      find ${path.module}/lambda-layers/python/ -type d -name "tests" -exec rm -rf {} +
      find ${path.module}/lambda-layers/python/ -type f -name "*.pyc" -delete
      find ${path.module}/lambda-layers/python/ -type d -name "*.dist-info" -exec rm -rf {} +
      find ${path.module}/lambda-layers/python/ -type d -name "*.egg-info" -exec rm -rf {} +
      cd ${path.module}/lambda-layers && zip -r python-dependencies.zip python/
    EOT
  }
}

resource "aws_lambda_function" "lambda-function" {
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  function_name    = "${var.function_name}"
  description   = "Lambda function for ${var.function_name}"
  handler       = "gmail_auto.handler"
  role          = module.iam_roles.lambda_role_arn
  runtime       = "python3.12"
  timeout       = 900
  memory_size   = 1024

  vpc_config {
    subnet_ids         = [var.subnet-id]
    security_group_ids = [var.security-group-id]
  }

  environment {
    variables = {
      GOOGLE_TOKEN_JSON     = var.google_token_json
      DESTINATION_EMAIL     = var.destination_email
      IMAGE_BUCKET          = var.image_bucket
      IMAGE_PREFIX          = var.image_prefix
      IMAGE_INDEX_SSM_PARAM = var.image_index_ssm_param
      EMAIL_BODY_TEXT       = var.email_body_text
    }
  }

  layers = [aws_lambda_layer_version.python_dependencies.arn]
  
  publish = true
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = module.event_bridge_triggers.cron_trigger_name
  target_id = "${var.function_name}"
  arn       = aws_lambda_function.lambda-function.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda-function.function_name
  principal     = "events.amazonaws.com"
  source_arn    = module.event_bridge_triggers.cron_trigger_arn
}
