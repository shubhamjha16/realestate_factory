"""
Uploader — Real Estate Factory
Uploads generated DOCX to S3; falls back to local file:// URL.
"""

import os, boto3
from botocore.exceptions import BotoCoreError, ClientError

S3_BUCKET  = os.environ.get("S3_BUCKET", "")
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")


def upload(local_path: str) -> str:
    if not S3_BUCKET:
        return f"file://{os.path.abspath(local_path)}"

    filename = os.path.basename(local_path)
    key      = f"realestate-factory/{filename}"

    try:
        client = boto3.client("s3", region_name=AWS_REGION)
        client.upload_file(
            local_path, S3_BUCKET, key,
            ExtraArgs={"ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        )
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=86400 * 7,
        )
        return url
    except (BotoCoreError, ClientError) as e:
        print(f"S3 upload failed: {e}")
        return f"file://{os.path.abspath(local_path)}"
