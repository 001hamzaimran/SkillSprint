import uvicorn
from app.config import Settings

if __name__ == "__main__":
    settings = Settings()
    uvicorn.run("app.main:create_app", factory=True, host="127.0.0.1", port=settings.port)
