import Main
import json

if __name__ == "__main__":
    # with open("test/transactions_create.json", "r") as fp:
    # with open("test/transactions_list.json", "r") as fp:        
    # with open("test/transactions_get.json", "r") as fp:        
    with open("test/transactions_edit.json", "r") as fp:        
        test_params = json.load(fp)
    result = Main.main(test_params, {})
    result['body'] = json.loads(result['body'])
    # with open("test/transactions_create_result.json", "w") as fp:
    # with open("test/transactions_list_result.json", "w") as fp:
    # with open("test/transactions_get_result.json", "w") as fp:
    #     json.dump(result, fp)