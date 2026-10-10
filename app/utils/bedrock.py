import boto3

# Nova Micro has no on-demand endpoint in ap-southeast-1 (the Lambda's
# region) -- only via this cross-region inference profile, which fans out
# to several APAC regions. Same per-token price as on-demand; the Lambda
# execution role needs bedrock:InvokeModel on both this inference-profile
# ARN and the underlying foundation-model ARN in each destination region.
MODEL_ID = "apac.amazon.nova-micro-v1:0"

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime")
    return _client


def converse(messages: list, system: list = None, tools: list = None) -> dict:
    kwargs = {"modelId": MODEL_ID, "messages": messages}
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["toolConfig"] = {"tools": tools}
    return _get_client().converse(**kwargs)
