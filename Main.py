from Params import Params
from Transactions import Main as Transactions
from Transactions import Group as TransactionGroups
from Attachments import Main as Attachments
from Locations import Main as Locations
import json
import re

routes = [
    ("/transactions", "GET", Transactions.list),
    ("/transactions", "POST", Transactions.create),
    (r"/transactions/\d+", "GET", Transactions.get),
    (r"/transactions/\d+", "PUT", Transactions.edit),
    (r"/transactions/\d+", "DELETE", Transactions.delete),
    (r"/transactions/groups", "GET", TransactionGroups.list),
    (r"/transactions/groups", "POST", TransactionGroups.create),
    (r"/transactions/groups/\d+", "GET", TransactionGroups.get),
    (r"/transactions/groups/\d+", "PUT", TransactionGroups.edit),
    (r"/transactions/groups/\d+", "DELETE", TransactionGroups.delete),
    (r"/attachments", "GET", Attachments.list),
    (r"/attachments", "POST", Attachments.create),
    (r"/attachments/\d+", "GET", Attachments.get),
    (r"/attachments/\d+", "PUT", Attachments.edit),
    (r"/attachments/\d+", "DELETE", Attachments.delete),
    (r"/locations", "GET", Locations.list),
    (r"/locations", "POST", Locations.create),
    (r"/locations/\d+", "GET", Locations.get),
    (r"/locations/\d+", "PUT", Locations.edit),
    (r"/locations/\d+", "DELETE", Locations.delete),    
]

def main(event, context):
    params = Params(event)
    for route_path, route_method, route_func in routes:
        if re.match(f"^{route_path}$", params.path) and (route_method == params.http_method):
            result = route_func(params)
            return {
                'statusCode': 200,
                'headers': {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "OPTIONS, GET, POST, PUT, DELETE",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                },
                'body': json.dumps(result)
            }
    return {
        'statusCode': 400,
        'body': json.dumps("Route doesn't exists")
    }

if __name__ == "__main__":
    pass