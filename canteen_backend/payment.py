def process_payment(method, amount):
    """
    Simulated payment processing for project
    """
    if method == "UPI":
        return {
            "status": "Paid",
            "transaction_id": "UPI" + str(int(amount * 100))
        }

    if method == "COD":
        return {
            "status": "Pending",
            "transaction_id": None
        }

    return {
        "status": "Failed",
        "transaction_id": None
    }
