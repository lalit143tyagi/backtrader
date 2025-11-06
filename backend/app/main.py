from fastapi import FastAPI

app = FastAPI(title="Trading Platform API")

@app.get("/health", summary="Health Check")
def health_check():
    """
    Simple health check endpoint to confirm the API is running.
    """
    return {"status": "ok"}
