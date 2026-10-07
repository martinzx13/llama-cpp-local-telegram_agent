from decimal import Decimal
from typing import Dict, Any


def calculate_ordinary_hour(salary: float) -> Decimal:
    """Ley 2466/2025: divisor 210 (42h/sem * 52 / 12)"""
    return Decimal(str(salary)) / Decimal("210")


def calculate_night_surcharge(ordinary_hour: Decimal, night_hours: float) -> Decimal:
    """Recargo nocturno 35% sobre hora ordinaria (Ley 2466/2025: noche desde 19:00)"""
    return ordinary_hour * Decimal("0.35") * Decimal(str(night_hours))


def calculate_sunday_surcharge(ordinary_hour: Decimal, sunday_hours: float, year: int = 2026) -> Decimal:
    """Recargo dominical/festivo: 90% (2026) → 100% (2027+)"""
    pct = Decimal("0.90") if year <= 2026 else Decimal("1.00")
    return ordinary_hour * pct * Decimal(str(sunday_hours))


def calculate_overtime_surcharge(ordinary_hour: Decimal, ot_hours: float, is_night: bool = False) -> Decimal:
    """Horas extra: 25% diurno, 75% nocturno (aditivo con recargos)"""
    pct = Decimal("0.75") if is_night else Decimal("0.25")
    return ordinary_hour * pct * Decimal(str(ot_hours))


def calculate_total_recargos(salary: float, hours_breakdown: Dict[str, float], year: int = 2026) -> Dict[str, Any]:
    """
    hours_breakdown: {
        'diurnas': float,
        'nocturnas': float,
        'dominicales': float,
        'extra_diurnas': float,
        'extra_nocturnas': float,
    }
    """
    ordinary = calculate_ordinary_hour(salary)
    nocturnas = hours_breakdown.get("nocturnas", 0)
    dominicales = hours_breakdown.get("dominicales", 0)
    extra_d = hours_breakdown.get("extra_diurnas", 0)
    extra_n = hours_breakdown.get("extra_nocturnas", 0)

    recargo_noche = calculate_night_surcharge(ordinary, nocturnas)
    recargo_dom = calculate_sunday_surcharge(ordinary, dominicales, year)
    recargo_extra_d = calculate_overtime_surcharge(ordinary, extra_d, False)
    recargo_extra_n = calculate_overtime_surcharge(ordinary, extra_n, True)

    total_recargos = recargo_noche + recargo_dom + recargo_extra_d + recargo_extra_n
    total_pagar = (ordinary * Decimal(str(sum(hours_breakdown.values())))) + total_recargos

    return {
        "hora_ordinaria": float(ordinary.quantize(Decimal("0.01"))),
        "recargo_nocturno": float(recargo_noche.quantize(Decimal("0.01"))),
        "recargo_dominical": float(recargo_dom.quantize(Decimal("0.01"))),
        "recargo_extra_diurno": float(recargo_extra_d.quantize(Decimal("0.01"))),
        "recargo_extra_nocturno": float(recargo_extra_n.quantize(Decimal("0.01"))),
        "total_recargos": float(total_recargos.quantize(Decimal("0.01"))),
        "total_pagar": float(total_pagar.quantize(Decimal("0.01"))),
    }


def get_shift_classification(hora_inicio: str, hora_fin: str) -> Dict[str, float]:
    """Clasifica horas de un turno en diurnas/nocturnas según Ley 2466 (noche desde 19:00)"""
    from datetime import datetime
    ini = datetime.strptime(hora_inicio, "%H:%M")
    fin = datetime.strptime(hora_fin, "%H:%M")

    if fin <= ini:
        fin = fin.replace(day=fin.day + 1)

    total_hours = (fin - ini).total_seconds() / 3600
    night_start = ini.replace(hour=19, minute=0)
    night_end = ini.replace(hour=6, minute=0) + timedelta(days=1)

    night_hours = 0
    current = ini
    while current < fin:
        if current >= night_start and current < night_end:
            night_hours += 1
        current += timedelta(hours=1)

    return {
        "total": total_hours,
        "nocturnas": night_hours,
        "diurnas": total_hours - night_hours,
    }