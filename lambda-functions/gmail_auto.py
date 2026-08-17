import os
import re
import json
import boto3
import tempfile
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.send']


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_image_number(filename):
    match = re.match(r'^(\d+)', filename)
    return int(match.group(1)) if match else float('inf')


def extract_subject_from_filename(filename: str) -> str:
    name_without_ext = os.path.splitext(filename)[0]
    clean_subject = re.sub(r'^\d+[\s\-_]*', '', name_without_ext).strip()
    return clean_subject if clean_subject else 'Dica do Dia - LGPD'


def get_s3_client():
    return boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'sa-east-1'))


def get_ssm_client():
    return boto3.client('ssm', region_name=os.environ.get('AWS_REGION', 'sa-east-1'))


# ---------------------------------------------------------------------------
# Credentials — JSON token directly in the environment variable
# ---------------------------------------------------------------------------

def get_valid_credentials() -> Credentials:
    """
    Loads the OAuth token from the GOOGLE_TOKEN_JSON environment variable.
    The value should be the full content of token-google-api.json as a JSON string.

    If the token is expired and there is a refresh_token, it is renewed
    automatically (no need to manually update the variable).
    """
    token_json = os.environ.get('GOOGLE_TOKEN_JSON')
    if not token_json:
        raise RuntimeError(
            "Environment variable GOOGLE_TOKEN_JSON not found. "
            "Paste the content of token-google-api.json into it."
        )

    token_info = json.loads(token_json)
    creds = Credentials.from_authorized_user_info(token_info, SCOPES)

    if creds.valid:
        return creds

    if creds.expired and creds.refresh_token:
        print("Token expired — renewing automatically…")
        creds.refresh(Request())
        return creds

    raise RuntimeError(
        "Invalid token and no refresh_token. "
        "Generate a new token locally and update the GOOGLE_TOKEN_JSON variable."
    )


# ---------------------------------------------------------------------------
# Images in S3
# ---------------------------------------------------------------------------

def list_images_from_s3(s3_client, bucket: str, prefix: str) -> list:
    paginator = s3_client.get_paginator('list_objects_v2')
    keys = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key.lower().endswith(('.jpg', '.jpeg', '.png')):
                keys.append(key)

    keys.sort(key=lambda k: get_image_number(os.path.basename(k)))
    return keys


def download_image_to_tmp(s3_client, bucket: str, key: str) -> str:
    filename = os.path.basename(key)
    local_path = os.path.join(tempfile.gettempdir(), filename)
    s3_client.download_file(bucket, key, local_path)
    return local_path


# ---------------------------------------------------------------------------
# Index control — SSM
# ---------------------------------------------------------------------------

def load_index(ssm_client, param_name: str) -> int:
    try:
        response = ssm_client.get_parameter(Name=param_name)
        return int(response['Parameter']['Value'])
    except Exception:
        return 0


def save_index(ssm_client, param_name: str, index: int):
    ssm_client.put_parameter(
        Name=param_name,
        Value=str(index),
        Type='String',
        Overwrite=True,
    )


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------

def handler(event, context):
    """
    Required environment variables in Lambda:

      GOOGLE_TOKEN_JSON       – content of token-google-api.json (JSON string)
      DESTINATION_EMAIL       – Recipient email address
      IMAGE_BUCKET            – S3 bucket with images
      IMAGE_PREFIX            – S3 image prefix (e.g., images/auto/)
      IMAGE_INDEX_SSM_PARAM   – SSM parameter to store the current index
    """

    destination_email = os.environ.get('DESTINATION_EMAIL', '')
    bucket            = os.environ['IMAGE_BUCKET']
    prefix            = os.environ.get('IMAGE_PREFIX', 'images/auto/')
    index_param       = os.environ['IMAGE_INDEX_SSM_PARAM']
    body_text_raw     = os.environ.get('EMAIL_BODY_TEXT', '')
    body_text         = body_text_raw.replace('\\n', '\n')

    s3  = get_s3_client()
    ssm = get_ssm_client()

    # ── Credentials ───────────────────────────────────────────────────────────
    creds = get_valid_credentials()

    # ── Image selection ───────────────────────────────────────────────────────
    image_keys = list_images_from_s3(s3, bucket, prefix)
    if not image_keys:
        raise RuntimeError(f"No images found in s3://{bucket}/{prefix}")

    current_index = load_index(ssm, index_param)
    if current_index >= len(image_keys):
        current_index = 0

    selected_key   = image_keys[current_index]
    image_filename = os.path.basename(selected_key)
    print(f"Selected image [{current_index}]: {image_filename}")

    local_path = download_image_to_tmp(s3, bucket, selected_key)

    # ── Sending via Gmail API ──────────────────────────────────────────────
    gmail_service = build('gmail', 'v1', credentials=creds)

    print(f"Preparing email for: {destination_email}…")
    
    subject_text = extract_subject_from_filename(image_filename)
    print(f"Setting email subject to: {subject_text}")

    message = MIMEMultipart('related')
    message['to'] = destination_email
    message['subject'] = subject_text

    # Convert newlines to HTML <br> tags for email body formatting
    html_body_text = body_text.replace('\n', '<br>')
    html_content = f"""\
<html>
  <body style="font-family: Arial, sans-serif; font-size: 14px; color: #333333; line-height: 1.5;">
    <div>{html_body_text}</div>
    <br>
    <div><img src="cid:tip_image" alt="{image_filename}" style="max-width: 600px; width: auto; height: auto; display: block; border-radius: 4px;"></div>
  </body>
</html>
"""
    message.attach(MIMEText(html_content, 'html', 'utf-8'))

    with open(local_path, 'rb') as f:
        img_data = f.read()
        image = MIMEImage(img_data)
        image.add_header('Content-ID', '<tip_image>')
        image.add_header('Content-Disposition', 'inline', filename=image_filename)
        message.attach(image)

    # Gmail API requires the message to be base64url encoded
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    print("Sending email…")
    gmail_service.users().messages().send(
        userId='me',
        body={'raw': raw_message}
    ).execute()

    print("Email sent successfully!")

    # ── Advance index ───────────────────────────────────────────────────────
    next_index = (current_index + 1) % len(image_keys)
    save_index(ssm, index_param, next_index)
    print(f"Next index saved: {next_index}")

    return {'statusCode': 200, 'body': f'Email sent with image: {image_filename}'}