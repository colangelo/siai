from fastapi import FastAPI

app = FastAPI(title="Demo App", description="Demo application for Woodpecker CI")


@app.get("/")
def root():
    """Root endpoint returning a welcome message."""
    return {"message": "Hello from Woodpecker CI!"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
