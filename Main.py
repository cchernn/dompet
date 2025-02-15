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
    ("/transactions/\d+", "GET", Transactions.get),
    ("/transactions/\d+", "PUT", Transactions.edit),
    ("/transactions/\d+", "DELETE", Transactions.delete),
    ("/transactions/groups", "GET", TransactionGroups.list),
    ("/transactions/groups", "POST", TransactionGroups.create),
    ("/transactions/groups/\d+", "GET", TransactionGroups.get),
    ("/transactions/groups/\d+", "PUT", TransactionGroups.edit),
    ("/transactions/groups/\d+", "DELETE", TransactionGroups.delete),
    ("/attachments", "GET", Attachments.list),
    ("/attachments", "POST", Attachments.create),
    ("/attachments/\d+", "GET", Attachments.get),
    ("/attachments/\d+", "PUT", Attachments.edit),
    ("/attachments/\d+", "DELETE", Attachments.delete),
    ("/locations", "GET", Locations.list),
    ("/locations", "POST", Locations.create),
    ("/locations/\d+", "GET", Locations.get),
    ("/locations/\d+", "PUT", Locations.edit),
    ("/locations/\d+", "DELETE", Locations.delete),    
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