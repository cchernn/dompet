event = {
    "resource": "/transactions",
    "path": "/transactions",
    "httpMethod": "GET",
    "headers": {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Authorization": "Bearer eyJraWQiOiI0bGJMMHgzeTB1R1k1QjA4RUVYelJ5bXBnU0tpcEFDVmxGdVRIK21VUEdjPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiI5OTlhMDViYy03MGUxLTcwM2QtOWVlYy1kZjZmZDIwYjgxMTMiLCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAuYXAtc291dGhlYXN0LTEuYW1hem9uYXdzLmNvbVwvYXAtc291dGhlYXN0LTFfZHd5Y3h6WHVEIiwidmVyc2lvbiI6MiwiY2xpZW50X2lkIjoiNTdrOXF0ZDVkY3JzOGh2NGUwaG1mMjBrbmUiLCJvcmlnaW5fanRpIjoiNzE2NTg2NDQtYjNiZi00MGVhLWJkMzctODBhNjIzNDVhNzNmIiwiZXZlbnRfaWQiOiI3NjJmMzk1ZS1hMDdiLTRkMzgtYjg2NC1jN2IxOWM5ZWZiNDkiLCJ0b2tlbl91c2UiOiJhY2Nlc3MiLCJzY29wZSI6ImVtYWlsIiwiYXV0aF90aW1lIjoxNzI4MDk3ODg1LCJleHAiOjE3MjgxMDE0ODUsImlhdCI6MTcyODA5Nzg4NSwianRpIjoiNGUxMjdkMDEtNjA2ZS00ODk3LTk3ZjMtMDA5ZTMxZmVjMmJhIiwidXNlcm5hbWUiOiI5OTlhMDViYy03MGUxLTcwM2QtOWVlYy1kZjZmZDIwYjgxMTMifQ.un741nmLpDcaaf8ye3-GgB7qNJo7_6HN31sl65Nn0nnzB_wVm65mhZSKFlsY3vzt0OHef_ptr4EH9KTcll3zQ6Gteu2kfKKuGaUn4nAlAbf_fI5E7qI0F7XzcIvJbJ6Cyemgd1w7u2x33RX2ceY-mXpqgtWs-6IOnn3AK8euQrKQxTpu7jXdVdPiytwTipzQ4_4m_OfPSFKRflKc4jT7Ji2UhMIGqWPIFoI0w9LpmzC_S89CcRa49ew29wqAQyFsCBi9xgXJ3IWDC6E_MaHvmWXv4ca-FdIUCPp9uNQ_-ud5-KU59Grkc-z4wAI9_UOU0tb6r0B8914B-3_GBstcbw",
        "Cache-Control": "no-cache",
        "Host": "df3r5hrar9.execute-api.ap-southeast-1.amazonaws.com",
        "Postman-Token": "f9c59ee3-b2b7-4eda-b552-b38a38ef4924",
        "User-Agent": "PostmanRuntime/7.42.0",
        "X-Amzn-Trace-Id": "Root=1-6700af98-377a194530b7c8b30b37a1cc",
        "X-Forwarded-For": "161.142.150.95",
        "X-Forwarded-Port": "443",
        "X-Forwarded-Proto": "https"
    },
    "multiValueHeaders": {
        "Accept": [
            "*/*"
        ],
        "Accept-Encoding": [
            "gzip, deflate, br"
        ],
        "Authorization": [
            "Bearer eyJraWQiOiI0bGJMMHgzeTB1R1k1QjA4RUVYelJ5bXBnU0tpcEFDVmxGdVRIK21VUEdjPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiI5OTlhMDViYy03MGUxLTcwM2QtOWVlYy1kZjZmZDIwYjgxMTMiLCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAuYXAtc291dGhlYXN0LTEuYW1hem9uYXdzLmNvbVwvYXAtc291dGhlYXN0LTFfZHd5Y3h6WHVEIiwidmVyc2lvbiI6MiwiY2xpZW50X2lkIjoiNTdrOXF0ZDVkY3JzOGh2NGUwaG1mMjBrbmUiLCJvcmlnaW5fanRpIjoiNzE2NTg2NDQtYjNiZi00MGVhLWJkMzctODBhNjIzNDVhNzNmIiwiZXZlbnRfaWQiOiI3NjJmMzk1ZS1hMDdiLTRkMzgtYjg2NC1jN2IxOWM5ZWZiNDkiLCJ0b2tlbl91c2UiOiJhY2Nlc3MiLCJzY29wZSI6ImVtYWlsIiwiYXV0aF90aW1lIjoxNzI4MDk3ODg1LCJleHAiOjE3MjgxMDE0ODUsImlhdCI6MTcyODA5Nzg4NSwianRpIjoiNGUxMjdkMDEtNjA2ZS00ODk3LTk3ZjMtMDA5ZTMxZmVjMmJhIiwidXNlcm5hbWUiOiI5OTlhMDViYy03MGUxLTcwM2QtOWVlYy1kZjZmZDIwYjgxMTMifQ.un741nmLpDcaaf8ye3-GgB7qNJo7_6HN31sl65Nn0nnzB_wVm65mhZSKFlsY3vzt0OHef_ptr4EH9KTcll3zQ6Gteu2kfKKuGaUn4nAlAbf_fI5E7qI0F7XzcIvJbJ6Cyemgd1w7u2x33RX2ceY-mXpqgtWs-6IOnn3AK8euQrKQxTpu7jXdVdPiytwTipzQ4_4m_OfPSFKRflKc4jT7Ji2UhMIGqWPIFoI0w9LpmzC_S89CcRa49ew29wqAQyFsCBi9xgXJ3IWDC6E_MaHvmWXv4ca-FdIUCPp9uNQ_-ud5-KU59Grkc-z4wAI9_UOU0tb6r0B8914B-3_GBstcbw"
        ],
        "Cache-Control": [
            "no-cache"
        ],
        "Host": [
            "df3r5hrar9.execute-api.ap-southeast-1.amazonaws.com"
        ],
        "Postman-Token": [
            "f9c59ee3-b2b7-4eda-b552-b38a38ef4924"
        ],
        "User-Agent": [
            "PostmanRuntime/7.42.0"
        ],
        "X-Amzn-Trace-Id": [
            "Root=1-6700af98-377a194530b7c8b30b37a1cc"
        ],
        "X-Forwarded-For": [
            "161.142.150.95"
        ],
        "X-Forwarded-Port": [
            "443"
        ],
        "X-Forwarded-Proto": [
            "https"
        ]
    },
    "queryStringParameters": None,
    "multiValueQueryStringParameters": None,
    "pathParameters": None,
    "stageVariables": None,
    "requestContext": {
        "resourceId": "tsx4xc",
        "authorizer": {
            "claims": {
                "sub": "999a05bc-70e1-703d-9eec-df6fd20b8113",
                "iss": "https://cognito-idp.ap-southeast-1.amazonaws.com/ap-southeast-1_dwycxzXuD",
                "version": "2",
                "client_id": "57k9qtd5dcrs8hv4e0hmf20kne",
                "origin_jti": "71658644-b3bf-40ea-bd37-80a62345a73f",
                "event_id": "762f395e-a07b-4d38-b864-c7b19c9efb49",
                "token_use": "access",
                "scope": "email",
                "auth_time": "1728097885",
                "exp": "Sat Oct 05 04:11:25 UTC 2024",
                "iat": "Sat Oct 05 03:11:25 UTC 2024",
                "jti": "4e127d01-606e-4897-97f3-009e31fec2ba",
                "username": "999a05bc-70e1-703d-9eec-df6fd20b8113"
            }
        },
        "resourcePath": "/transactions",
        "httpMethod": "GET",
        "extendedRequestId": "fKBf1GFTyQ0EHnQ=",
        "requestTime": "05/Oct/2024:03:16:40 +0000",
        "path": "/staging/transactions",
        "accountId": "184428541421",
        "protocol": "HTTP/1.1",
        "stage": "staging",
        "domainPrefix": "df3r5hrar9",
        "requestTimeEpoch": 1728098200299,
        "requestId": "b67e03a6-faff-4ea1-9779-84970836909d",
        "identity": {
            "cognitoIdentityPoolId": None,
            "accountId": None,
            "cognitoIdentityId": None,
            "caller": None,
            "sourceIp": "161.142.150.95",
            "principalOrgId": None,
            "accessKey": None,
            "cognitoAuthenticationType": None,
            "cognitoAuthenticationProvider": None,
            "userArn": None,
            "userAgent": "PostmanRuntime/7.42.0",
            "user": None
        },
        "domainName": "df3r5hrar9.execute-api.ap-southeast-1.amazonaws.com",
        "deploymentId": "vsh9oy",
        "apiId": "df3r5hrar9"
    },
    "body": None,
    "isBase64Encoded": False
}