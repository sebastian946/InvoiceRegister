from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routes.routes import router
from utils.config_env import settings

BASE_DIR = Path(__file__).resolve().parent

# Where the built React app may live, in priority order: inside the container
# image, then the local build output of `npm run build`.
FRONTEND_CANDIDATES = [BASE_DIR / "static", BASE_DIR.parent / "frontend" / "dist"]


def find_frontend_dir(candidates: list[Path] | None = None) -> Path | None:
    """Return the first folder that holds a built frontend, or None."""
    if candidates is None:
        explicit = [Path(settings.frontend_dir)] if settings.frontend_dir else []
        candidates = explicit + FRONTEND_CANDIDATES
    for folder in candidates:
        if (folder / "index.html").is_file():
            return folder
    return None


def mount_frontend(application: FastAPI, folder: Path | None) -> bool:
    """Serve the frontend at "/". Call it last: a mount at "/" catches every
    path that no earlier route matched, so API routes must be registered first.
    """
    if folder is None:
        return False
    application.mount("/", StaticFiles(directory=folder, html=True), name="frontend")
    return True


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


# Without a built frontend the API still works on its own.
mount_frontend(app, find_frontend_dir())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=settings.debug)
