from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader
from bot.config import get_settings
import os


def generate_certificate_pdf(cert_data: dict, tipo: str, destino: str) -> str:
    config = get_settings()
    env = Environment(loader=FileSystemLoader("bot/templates"))
    template = env.get_template(f"certificado_{tipo}.html")

    html = template.render(
        empleado=cert_data,
        tipo=tipo,
        destino=destino,
        fecha_emision=datetime.now().strftime("%d/%m/%Y"),
    )

    output_dir = "/app/data/certificados"
    os.makedirs(output_dir, exist_ok=True)
    filename = f"cert_{tipo}_{cert_data['id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf_path = os.path.join(output_dir, filename)

    HTML(string=html).write_pdf(pdf_path)
    return pdf_path


from datetime import datetime