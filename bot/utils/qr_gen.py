import qrcode
from bot.config import get_settings


def generate_qr(cert_id: int, pdf_path: str, base_url: str) -> str:
    verify_url = f"{base_url}/{cert_id}"
    qr = qrcode.make(verify_url)
    qr_path = pdf_path.replace(".pdf", "_qr.png")
    qr.save(qr_path)
    return verify_url