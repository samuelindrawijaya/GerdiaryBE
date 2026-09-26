from __future__ import annotations

RED_FLAG_VERSION = "1"

RF_CHEST_PAIN = "RF_CHEST_PAIN"
RF_VOMIT_BLOOD = "RF_VOMIT_BLOOD"
RF_BLACK_STOOL = "RF_BLACK_STOOL"
RF_DYSPHAGIA_SEVERE = "RF_DYSPHAGIA_SEVERE"

ALL_CODES = (
    RF_CHEST_PAIN,
    RF_VOMIT_BLOOD,
    RF_BLACK_STOOL,
    RF_DYSPHAGIA_SEVERE,
)

_COPY: dict[str, tuple[str, str]] = {
    RF_CHEST_PAIN: (
        "Nyeri dada",
        "Nyeri dada bisa menjadi tanda kondisi serius. Segera hubungi dokter atau pergi ke IGD terdekat.",  # noqa: E501
    ),
    RF_VOMIT_BLOOD: (
        "Muntah darah",
        "Muntah darah bisa menjadi tanda kondisi serius. Segera hubungi dokter atau pergi ke IGD terdekat.",  # noqa: E501
    ),
    RF_BLACK_STOOL: (
        "BAB berwarna hitam",
        "BAB berwarna hitam bisa menjadi tanda perdarahan saluran cerna. Segera hubungi dokter atau pergi ke IGD terdekat.",  # noqa: E501
    ),
    RF_DYSPHAGIA_SEVERE: (
        "Sulit menelan parah",
        "Kesulitan menelan yang parah bisa menjadi tanda kondisi serius. Segera hubungi dokter atau pergi ke IGD terdekat.",  # noqa: E501
    ),
}


def code_for(symptom: str, severity: str) -> str | None:
    if symptom == "chest_pain":
        return RF_CHEST_PAIN
    if symptom == "vomit_blood":
        return RF_VOMIT_BLOOD
    if symptom == "black_stool":
        return RF_BLACK_STOOL
    if symptom == "difficulty_swallowing" and severity == "severe":
        return RF_DYSPHAGIA_SEVERE
    return None


def payload(code: str) -> dict[str, str]:
    title, message = _COPY[code]
    return {
        "code": code,
        "version": RED_FLAG_VERSION,
        "title": title,
        "message": message,
    }
