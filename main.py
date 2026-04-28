import uvicorn
import os

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5001"))

if __name__ == "__main__":
    uvicorn.run("routes.routes:app", host=HOST, port=PORT, reload=True)
