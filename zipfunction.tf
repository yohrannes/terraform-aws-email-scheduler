data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda-functions/gmail_auto.py"
  output_path = "${path.module}/lambda-functions/lambda-function.zip"
}
