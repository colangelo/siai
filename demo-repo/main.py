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


if __name__ == "__main__":
    import asyncio
    import sys

    import uvicorn

    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    # Disable uvicorn's signal handlers - let tini handle SIGINT/SIGTERM
    server.install_signal_handlers = lambda: None
    try:
        asyncio.run(server.serve())
    except (KeyboardInterrupt, asyncio.CancelledError):
        sys.exit(0)  # Clean exit
