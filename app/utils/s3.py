import boto3

from . import config

UPLOAD_URL_EXPIRY_SECONDS = 5 * 60
DOWNLOAD_URL_EXPIRY_SECONDS = 15 * 60

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client("s3")
    return _client


def generate_upload_url(key: str, content_type: str = None) -> str:
    params = {"Bucket": config.ATTACHMENTS_S3_BUCKET, "Key": key}
    if content_type:
        params["ContentType"] = content_type
    return _get_client().generate_presigned_url(
        "put_object", Params=params, ExpiresIn=UPLOAD_URL_EXPIRY_SECONDS
    )


def generate_download_url(key: str) -> str:
    return _get_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": config.ATTACHMENTS_S3_BUCKET, "Key": key},
        ExpiresIn=DOWNLOAD_URL_EXPIRY_SECONDS,
    )


def delete_object(key: str) -> None:
    _get_client().delete_object(Bucket=config.ATTACHMENTS_S3_BUCKET, Key=key)
