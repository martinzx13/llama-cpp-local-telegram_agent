from bot.skills.base import BaseSkill, SkillResult
from bot.utils.pdf_gen import generate_certificate_pdf
from bot.utils.qr_gen import generate_qr
from bot.utils.pin import verify_pin
import os


class CertificadosSkill(BaseSkill):
    name = "certificados"
    description = "Generación de certificados (laboral, tiempos, salario) con QR de verificación"
    allowed_intents = ["certificado_laboral", "certificado_tiempos", "certificado_salario"]
    permission = "empleado"
    tools = ["sqlite", "pdf_gen", "qr_gen"]
    input_schema = {
        "tipo": {"type": "string", "enum": ["laboral", "tiempos", "salario"]},
        "destino": {"type": "string", "minLength": 3},
    }
    validation = {
        "tipo": "required",
        "destino": "required",
    }

    async def execute(self, user_id: int, intent: str, args: Dict) -> SkillResult:
        tipo_map = {
            "certificado_laboral": "laboral",
            "certificado_tiempos": "tiempos",
            "certificado_salario": "salario",
        }
        tipo = tipo_map.get(intent, args.get("tipo", "laboral"))
        destino = args.get("destino", "").strip()

        if not destino:
            return SkillResult(False, "Debe indicar el destino del certificado.")

        user = self.db.get_user(user_id)
        if not user:
            return SkillResult(False, "Usuario no encontrado en el sistema.")

        if tipo == "salario":
            pin_ok = await verify_pin(user_id, self.db, self.config)
            if not pin_ok:
                return SkillResult(False, "PIN incorrecto o bloqueado. Contacte a Talento Humano.")

        cert_data = self.db.get_certificate_data(user_id, tipo)
        if not cert_data:
            return SkillResult(False, "No se encontraron datos para generar el certificado.")

        pdf_path = generate_certificate_pdf(cert_data, tipo, destino)
        qr_hash = generate_qr(cert_data["id"], pdf_path, self.config.pdf.qr_base_url)

        self.db.log_certificate(user_id, tipo, destino, pdf_path, qr_hash)
        await self.log_action(user_id, "generate_certificate", "certificado", cert_data["id"], {
            "tipo": tipo, "destino": destino, "qr_hash": qr_hash
        })

        return SkillResult(
            success=True,
            message=f"✅ Certificado {tipo} generado para {destino}.",
            data={"pdf_path": pdf_path, "qr_hash": qr_hash},
            files=[pdf_path],
        )