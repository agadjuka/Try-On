import os

import boto3
from botocore.config import Config

endpoint = os.getenv("ORACLE_S3_ENDPOINT")
region = os.getenv("ORACLE_S3_REGION", "me-dubai-1")
access_key = os.getenv("ORACLE_ACCESS_KEY_ID")
secret_key = os.getenv("ORACLE_SECRET_ACCESS_KEY")
bucket = os.getenv("ORACLE_BUCKET_NAME", "vyon_files")

if not endpoint or not access_key or not secret_key:
    raise RuntimeError(
        "Укажи ORACLE_S3_ENDPOINT, ORACLE_ACCESS_KEY_ID, ORACLE_SECRET_ACCESS_KEY"
    )

s3 = boto3.client(
    "s3",
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    endpoint_url=endpoint,
    region_name=region,
    config=Config(
        signature_version="s3v4",
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
        s3={
            "addressing_style": "path",
            "payload_signing_enabled": False,
        },
    ),
)

try:
    print("Пробуем загрузить файл...")
    body = b"It works perfectly!"
    s3.put_object(
        Bucket=bucket,
        Key="test_upload.txt",
        Body=body,
        ContentLength=len(body),
    )
    print("УСПЕХ! Файл test_upload.txt загружен в бакет.")

    print("Пробуем прочитать файл обратно...")
    response = s3.get_object(Bucket=bucket, Key="test_upload.txt")
    print("Содержимое:", response["Body"].read().decode("utf-8"))

except Exception as e:
    print(f"Ошибка: {e}")
