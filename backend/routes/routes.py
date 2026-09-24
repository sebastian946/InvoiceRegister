import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from controllers.invoice_controller import read_invoice, register_invoice
from models.models import FileUploadResponse

router = APIRouter(prefix="/invoices", tags=["invoices"])

PATH_FOLDER = Path(__file__).resolve().parent.parent / "files_upload"
ALLOWED_CONTENT_TYPES = {"application/pdf"}


def save_upload(file: UploadFile) -> Path:
    """Store the uploaded file inside PATH_FOLDER and return its path.

    The client-supplied name is reduced to its last component, so a crafted
    filename such as "../../etc/passwd" cannot escape the upload folder.
    """
    safe_name = Path(file.filename or "").name
    if not safe_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file has no name.",
        )

    PATH_FOLDER.mkdir(parents=True, exist_ok=True)
    file_path = PATH_FOLDER / safe_name

    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except OSError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save the file: {error}",
        ) from error
    finally:
        file.file.close()

    return file_path


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    response_model=FileUploadResponse,
    summary="Upload an invoice PDF, extract its data and register it",
)
def upload_invoice(file: UploadFile = File(...), register: bool = True):
    """Read the invoice with the LLM and, unless `register=false`, write it to the sheet.

    Extraction takes tens of seconds, so clients need a generous timeout.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Format not allowed: {file.content_type}. Only PDF is accepted.",
        )

    file_path = save_upload(file)

    try:
        invoice = register_invoice(file_path) if register else read_invoice(file_path)
    except ValueError as error:
        # No readable text: an empty or unreadable scan
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    except Exception as error:
        # The LLM or Google Sheets refused the request
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not process the invoice: {error}",
        ) from error

    return FileUploadResponse(
        invoice=invoice,
        filename=file_path.name,
        registered=register,
    )
