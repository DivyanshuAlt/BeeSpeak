# rules/keyword_rules.py

CATEGORY_PRIORITY = [
    "ACCOUNT_THREAT",
    "PAYMENT_REQUEST",
    "URGENCY"
]

KEYWORD_CATEGORIES = {
    "ACCOUNT_THREAT": [
        "account will be blocked",
        "account suspended",
        "account suspension"
    ],
    "URGENCY": [
        "verify immediately",
        "urgent",
        "verify now",
        "immediately"
    ],
    "PAYMENT_REQUEST": [
        "share your upi",
        "send money",
        "pay now"
    ]
}
