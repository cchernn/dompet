from app.aws_lambda_handler import lambda_handler
import json

if __name__ == "__main__":
    files = [
        "transactions_list",
        "groups_list",
        "locations_list",
        "attachments_list"
        # "transactions_create",
        # "transactions_get",
        # "transactions_edit",
        # "transactions_delete",
        # "groups_create",
        # "locations_create",
    ]
    for filename in files:
        with open(f"test/params/{filename}.json", "r") as fp:
            event = json.load(fp)
        result = lambda_handler(event, None)
        result = json.loads(result)
        with open(f"test/results/{filename}.json", "w") as fp:
            json.dump(result, fp)
