class FahrenheitDTO:
    def __init__(self,
                 ctpl: float,
                 t_f68: float,
                 dtF: float,
                 p60: float,
                 pA: float,
                 B: float,
                 bB: float,
                 pStar: float,
                 alpha60: float,
                 ctl: float,
                 fs: float,
                 cpl: float,
                 ) -> None:
        self.ctpl = ctpl
        self.t_f68 = t_f68
        self.dtF = dtF
        self.p60 = p60
        self.pA = pA
        self.B = B
        self.bB = bB
        self.pStar = pStar
        self.alpha60 = alpha60
        self.ctl = ctl
        self.fs = fs
        self.cpl = cpl

    def toJson(self):
        return {
            'ctpl': self.ctpl,
            't_f68': self.t_f68,
            'dtF': self.dtF,
            'p60': self.p60,
            'pA': self.pA,
            'B': self.B,
            'bB': self.bB,
            'pStar': self.pStar,
            'alpha60': self.alpha60,
            'ctl': self.ctl,
            'fs': self.fs,
            'cpl': self.cpl,
        }


class TempConvDTO:
    def __init__(self,
                 t_f68_raw: float,
                 t_f68: float,
                 dt: float,
                 tau: float,
                 t_c90: float,
                 t_c68: float) -> None:
        self.t_f68_raw = t_f68_raw
        self.t_f68 = t_f68
        self.dt = dt
        self.tau = tau
        self.t_c90 = t_c90
        self.t_c68 = t_c68
