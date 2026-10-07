from bot.skills.certificados import CertificadosSkill
from bot.skills.vacaciones import VacacionesSkill
from bot.skills.consulta import ConsultaSkill

SKILLS = {
    "certificados": CertificadosSkill,
    "vacaciones": VacacionesSkill,
    "consulta": ConsultaSkill,
}


def get_skill_names() -> list:
    return list(SKILLS.keys())


def get_skill_class(name: str):
    return SKILLS.get(name)