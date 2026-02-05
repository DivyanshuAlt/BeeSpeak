#schemas/response_schema.py

"""Public response contract returned by the pipeline/API."""

def base_response():
    return {
        "status": "success",
        "reply": "",
    }
