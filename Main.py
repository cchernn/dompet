from Database import Database
from Params import Params
from Transactions import Main as Transactions
from Transactions import Group as TransactionGroups
import Setup
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
]

def main(event, context):
    params = Params(event)
    db = Database(params)
    for route_path, route_method, route_func in routes:
        if re.match(f"^{route_path}$", params.path) and (route_method == params.http_method):
            result = route_func(params, db)
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
    return {
        'statusCode': 400,
        'body': json.dumps("Route doesn't exists")
    }

def admin(event, context):
    params = Params(event)
    db = Database(params)
    Setup.main(params, db)
