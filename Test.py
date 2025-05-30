from app.aws_lambda_handler import lambda_handler
import json

if __name__ == "__main__":
    files = [
        # "transactions_list",
        # "transactions_create", # pending group and attachment
        # "transactions_get",
        # "transactions_edit", # pending group and attachment
        # "transactions_delete",
        # "groups_list", 
        # "groups_create", # pending user
        # "groups_get",
        # "groups_edit", # pending user
        # "groups_delete",
        # "locations_list",
        # "locations_create",
        # "locations_get",
        # "locations_edit",
        # "locations_delete",
        # "attachments_list"
        # "attachments_create"
        # "attachments_get"
        # "attachments_edit"
        # "attachments_delete"
    ]
    for filename in files:
        with open(f"test/params/{filename}.json", "r") as fp:
            event = json.load(fp)
        result = lambda_handler(event, None)
        result = json.loads(result)
        with open(f"test/results/{filename}.json", "w") as fp:
            json.dump(result, fp)
