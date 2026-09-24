import os

import boto3

UPLOAD_URL_EXPIRY_SECONDS = 5 * 60
DOWNLOAD_URL_EXPIRY_SECONDS = 15 * 60

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client("s3")
    return _client


def _bucket() -> str:
    # Read lazily (not a config.py module-level constant) so this works
    # whether the env var came from real Lambda env vars (set before the
    # process starts) or from load_local_env() (only runs inside a script's
    # main(), after this module has already been imported).
    return os.getenv("ATTACHMENTS_S3_BUCKET")


def generate_upload_url(key: str, content_type: str = None) -> str:
    params = {"Bucket": _bucket(), "Key": key}
    if content_type:
        params["ContentType"] = content_type
    return _get_client().generate_presigned_url(
        "put_object", Params=params, ExpiresIn=UPLOAD_URL_EXPIRY_SECONDS
    )


def generate_download_url(key: str) -> str:
    return _get_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": _bucket(), "Key": key},
        ExpiresIn=DOWNLOAD_URL_EXPIRY_SECONDS,
    )


def delete_object(key: str) -> None:
    _get_client().delete_object(Bucket=_bucket(), Key=key)
