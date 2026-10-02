import math
from dataclasses import dataclass
from typing import Optional, Tuple

from constants import API_FACTOR_TABLE_A, API_FACTOR_TABLE_B
from models import FahrenheitDTO, TempConvDTO

WATER_DENSITY_60F = 999.016  # kg/m³ (densidade da água a 60°F)
DELTA60_DEFAULT = 0.01374979547  # δ60 informado
TEMP68_REF_F = 60.0068749  # p/ Dt = tF(68) - TEMP68_REF_F


def round_dec(x: float, d: int) -> float:
    p = 10 ** d
    return round((x + float.fromhex("0x1.0p-52")) * p) / p  # similar a EPSILON


def calculate_dt(tau: float) -> float:
    a1 = -0.148759;
    a2 = -0.267408;
    a3 = 1.080760;
    a4 = 1.269056
    a5 = -4.089591;
    a6 = -1.871251;
    a7 = 7.438081;
    a8 = -3.536296
    s = a8 * tau
    s = (a7 + s) * tau
    s = (a6 + s) * tau
    s = (a5 + s) * tau
    s = (a4 + s) * tau
    s = (a3 + s) * tau
    s = (a2 + s) * tau
    s = (a1 + s) * tau
    return s


def temperature_conversion_its90_to_ipts68(input_temp_f_its90: float) -> TempConvDTO:
    t_c90 = (input_temp_f_its90 - 32.0) / 1.8
    tau = t_c90 / 630.0
    dt = calculate_dt(tau)
    t_c68 = t_c90 - dt
    t_f68_raw = t_c68 * 1.8 + 32.0
    return TempConvDTO(
        t_f68_raw=t_f68_raw,
        t_f68=round_dec(t_f68_raw, 4),
        dt=round_dec(dt, 9),
        tau=round_dec(tau, 7),
        t_c90=round_dec(t_c90, 2),
        t_c68=round_dec(t_c68, 8),
    )


def density_p60_from_api(api60: float) -> float:
    # 141.5 / (API + 131.5) * densidade água a 60°F
    return (141.5 / (api60 + 131.5)) * WATER_DENSITY_60F


def pick_coeffs_for_a(api60: float) -> Optional[Tuple[float, float, float]]:
    for lo, hi, ag, ah, ai in API_FACTOR_TABLE_A:
        if api60 >= lo and api60 <= hi:
            return ag, ah, ai
    return None


def pick_coeffs_for_b_like(api60: float) -> Optional[Tuple[float, float, float]]:
    for i, (lo, hi, ag, ah, ai) in enumerate(API_FACTOR_TABLE_B):
        if i == 0:
            if api60 >= lo and api60 <= hi:
                return ag, ah, ai
        else:
            if api60 > lo and api60 <= hi:
                return ag, ah, ai
    return None


def compute_pA_by_api(api60: float, p60: float, delta60: float = DELTA60_DEFAULT) -> float:
    """p*A, B, α60, CTL, Fs, CPL, CTPL e ρ*"""
    coeffs = pick_coeffs_for_a(api60)
    if coeffs is None:
        return float("nan")
    ag, ah, ai = coeffs
    return (delta60 / 2.0) * ((ag / p60) + ah) * (1.0 / p60) + ai


def compute_B_by_api(api60: float, p60: float) -> float:
    coeffs = pick_coeffs_for_b_like(api60)
    if coeffs is None:
        return float("nan")
    ag, ah, ai = coeffs
    return (2.0 * ag + ah * p60) / (ag + (ah + ai * p60) * p60)


def compute_alpha60_by_api(api60: float, pstar: float) -> float:
    coeffs = pick_coeffs_for_b_like(api60)
    if coeffs is None:
        return float("nan")
    ag, ah, ai = coeffs
    return ((ag / pstar) + ah) * (1.0 / pstar) + ai


def compute_ctl(alpha60: float, dtF: float, delta60: float = DELTA60_DEFAULT) -> float:
    dt_used = round_dec(dtF, 7)
    return math.exp(-alpha60 * dt_used * (1.0 + 0.8 * alpha60 * (dt_used + delta60)))


def compute_fs(tF68_raw: float, pstar: float) -> float:
    return math.exp(-1.9947 + 0.00013427 * tF68_raw + ((793920.0 + 2326.0 * tF68_raw) / (pstar * pstar)))


def compute_cpl(fs: float, pressure_psig: float = 0.0) -> float:
    return 1.0 / (1.0 - fs * pressure_psig * 1e-5)


def compute_rho_star(p60: float, pA: float, bB: float) -> float:
    num = math.exp(pA * (1.0 + 0.8 * pA)) - 1.0
    den = 1.0 + pA * (1.0 + 1.6 * pA) * bB
    return p60 * (1.0 + (num / den))


@dataclass(frozen=True)
class Result:
    ctpl: float
    t_f68: float
    dtF: float
    p60: float
    pA: float
    B: float
    bB: float
    pStar: float
    alpha60: float
    ctl: float
    fs: float
    cpl: float


def toFahrenheit(temp_f_its90: float, api60: float, pressure_psig: float = 0.0,
                 delta60: float = DELTA60_DEFAULT) -> Result:
    # 1) ITS-90 -> IPTS-68
    conv = temperature_conversion_its90_to_ipts68(temp_f_its90)
    tF68_raw = conv.t_f68_raw
    dtF = tF68_raw - TEMP68_REF_F

    # 2) p60 via API
    p60 = density_p60_from_api(api60)

    # 3) p*A, B, bB, p*
    pA = compute_pA_by_api(api60, p60, delta60)
    B = compute_B_by_api(api60, p60)
    bB = delta60 * B
    pStar = compute_rho_star(p60, pA, bB)

    # 4) α60, CTL, Fs, CPL, CTPL
    alpha60 = compute_alpha60_by_api(api60, pStar)
    ctl = compute_ctl(alpha60, dtF, delta60)
    fs = compute_fs(tF68_raw, pStar)
    cpl = compute_cpl(fs, pressure_psig)
    ctpl = cpl * ctl

    return FahrenheitDTO(
        ctpl=ctpl,
        t_f68=conv.t_f68,
        dtF=dtF,
        p60=p60,
        pA=pA,
        B=B,
        bB=bB,
        pStar=pStar,
        alpha60=alpha60,
        ctl=ctl,
        fs=fs,
        cpl=cpl
    ).toJson()
