from typing import overload

from .typedefs import Number


class TetrisMetricsBaseWithPPS:
    def __init__(self, pps: Number, precision: int) -> None:
        self._pps = pps
        self.precision = precision

    @property
    def _lpm(self) -> Number:
        return self._pps * 24

    @property
    def lpm(self) -> Number:
        return round(self._lpm, self.precision)

    @property
    def pps(self) -> Number:
        return round(self._pps, self.precision)


class TetrisMetricsBaseWithLPM:
    def __init__(self, lpm: Number, precision: int) -> None:
        self._lpm = lpm
        self.precision = precision

    @property
    def lpm(self) -> Number:
        return round(self._lpm, self.precision)

    @property
    def _pps(self) -> Number:
        return self._lpm / 24

    @property
    def pps(self) -> Number:
        return round(self._pps, self.precision)


class TetrisMetricsBaseWithVS:
    def __init__(self, vs: Number, precision: int) -> None:
        self._vs = vs
        self.precision = precision

    @property
    def vs(self) -> Number:
        return round(self._vs, self.precision)

    @property
    def _adpm(self) -> Number:
        return self._vs * 0.6

    @property
    def adpm(self) -> Number:
        return round(self._adpm, self.precision)


class TetrisMetricsBaseWithADPM:
    def __init__(self, adpm: Number, precision: int) -> None:
        self._adpm = adpm
        self.precision = precision

    @property
    def _vs(self) -> Number:
        return self._adpm / 0.6

    @property
    def vs(self) -> Number:
        return round(self._vs, self.precision)

    @property
    def adpm(self) -> Number:
        return round(self._adpm, self.precision)


class TetrisMetricsBasicWithPPS(TetrisMetricsBaseWithPPS):
    def __init__(self, pps: Number, apm: Number, precision: int) -> None:
        super().__init__(pps=pps, precision=precision)
        self._apm = apm

    @property
    def apm(self) -> Number:
        return round(self._apm, self.precision)

    @property
    def apl(self) -> Number:
        return round(self._apm / self._lpm, self.precision)


class TetrisMetricsBasicWithLPM(TetrisMetricsBaseWithLPM):
    def __init__(self, lpm: Number, apm: Number, precision: int):
        super().__init__(lpm=lpm, precision=precision)
        self._apm = apm

    @property
    def apm(self) -> Number:
        return round(self._apm, self.precision)

    @property
    def apl(self) -> Number:
        return round(self._apm / self._lpm, self.precision)


class TetrisMetricsProWithPPSVS(TetrisMetricsBasicWithPPS, TetrisMetricsBaseWithVS):
    def __init__(self, pps: Number, apm: Number, vs: Number, precision: int) -> None:
        super().__init__(pps=pps, apm=apm, precision=precision)
        super(TetrisMetricsBaseWithPPS, self).__init__(vs=vs, precision=precision)

    @property
    def adpl(self) -> Number:
        return round(self._adpm / self._lpm, self.precision)


class TetrisMetricsProWithPPSADPM(TetrisMetricsBasicWithPPS, TetrisMetricsBaseWithADPM):
    def __init__(self, pps: Number, apm: Number, adpm: Number, precision: int) -> None:
        super().__init__(pps=pps, apm=apm, precision=precision)
        super(TetrisMetricsBaseWithPPS, self).__init__(adpm=adpm, precision=precision)

    @property
    def adpl(self) -> Number:
        return round(self._adpm / self._lpm, self.precision)


class TetrisMetricsProWithLPMVS(TetrisMetricsBasicWithLPM, TetrisMetricsBaseWithVS):
    def __init__(self, lpm: Number, apm: Number, vs: Number, precision: int) -> None:
        super().__init__(lpm=lpm, apm=apm, precision=precision)
        super(TetrisMetricsBaseWithLPM, self).__init__(vs=vs, precision=precision)

    @property
    def adpl(self) -> Number:
        return round(self._adpm / self._lpm, self.precision)


class TetrisMetricsProWithLPMADPM(TetrisMetricsBasicWithLPM, TetrisMetricsBaseWithADPM):
    def __init__(self, lpm: Number, apm: Number, adpm: Number, precision: int) -> None:
        super().__init__(lpm=lpm, apm=apm, precision=precision)
        super(TetrisMetricsBaseWithLPM, self).__init__(adpm=adpm, precision=precision)

    @property
    def adpl(self) -> Number:
        return round(self._adpm / self._lpm, self.precision)


@overload
def get_metrics(
    *,
    pps: Number,
    precision: int = 2,
) -> TetrisMetricsBaseWithPPS: ...


@overload
def get_metrics(
    *,
    lpm: Number,
    precision: int = 2,
) -> TetrisMetricsBaseWithLPM: ...


@overload
def get_metrics(
    *,
    vs: Number,
    precision: int = 2,
) -> TetrisMetricsBaseWithVS: ...


@overload
def get_metrics(
    *,
    adpm: Number,
    precision: int = 2,
) -> TetrisMetricsBaseWithADPM: ...


@overload
def get_metrics(
    *,
    pps: Number,
    apm: Number,
    precision: int = 2,
) -> TetrisMetricsBasicWithPPS: ...


@overload
def get_metrics(
    *,
    lpm: Number,
    apm: Number,
    precision: int = 2,
) -> TetrisMetricsBasicWithLPM: ...


@overload
def get_metrics(
    *,
    pps: Number,
    apm: Number,
    vs: Number,
    precision: int = 2,
) -> TetrisMetricsProWithPPSVS: ...


@overload
def get_metrics(
    *,
    pps: Number,
    apm: Number,
    adpm: Number,
    precision: int = 2,
) -> TetrisMetricsProWithPPSADPM: ...


@overload
def get_metrics(
    *,
    lpm: Number,
    apm: Number,
    vs: Number,
    precision: int = 2,
) -> TetrisMetricsProWithLPMVS: ...


@overload
def get_metrics(
    *,
    lpm: Number,
    apm: Number,
    adpm: Number,
    precision: int = 2,
) -> TetrisMetricsProWithLPMADPM: ...


def get_metrics(  # noqa: PLR0911, PLR0912, PLR0913, C901
    *,
    pps: Number | None = None,
    lpm: Number | None = None,
    apm: Number | None = None,
    vs: Number | None = None,
    adpm: Number | None = None,
    precision: int = 2,
) -> (
    TetrisMetricsBaseWithPPS
    | TetrisMetricsBaseWithLPM
    | TetrisMetricsBaseWithVS
    | TetrisMetricsBaseWithADPM
    | TetrisMetricsBasicWithPPS
    | TetrisMetricsBasicWithLPM
    | TetrisMetricsProWithPPSVS
    | TetrisMetricsProWithLPMVS
    | TetrisMetricsProWithPPSADPM
    | TetrisMetricsProWithLPMADPM
):
    if apm is None:
        if pps is not None:
            return TetrisMetricsBaseWithPPS(pps, precision=precision)
        if lpm is not None:
            return TetrisMetricsBaseWithLPM(lpm, precision=precision)
        if vs is not None:
            return TetrisMetricsBaseWithVS(vs, precision=precision)
        if adpm is not None:
            return TetrisMetricsBaseWithADPM(adpm, precision=precision)
    elif vs is None and adpm is None:
        if pps is not None:
            return TetrisMetricsBasicWithPPS(pps, apm, precision=precision)
        if lpm is not None:
            return TetrisMetricsBasicWithLPM(lpm, apm, precision=precision)
    else:
        if vs is not None:
            if pps is not None:
                return TetrisMetricsProWithPPSVS(pps, apm, vs, precision=precision)
            if lpm is not None:
                return TetrisMetricsProWithLPMVS(lpm, apm, vs, precision=precision)
        if adpm is not None:
            if pps is not None:
                return TetrisMetricsProWithPPSADPM(pps, apm, adpm, precision=precision)
            if lpm is not None:
                return TetrisMetricsProWithLPMADPM(lpm, apm, adpm, precision=precision)

    raise TypeError
