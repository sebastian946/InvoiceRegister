from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.routes import router
from utils.config_env import settings

app = FastAPI(title="Invoice Register", debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)


@app.get("/Health", summary="Health check endpoint")
def root():
    return {"message": "Health check OK", "status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=settings.debug)