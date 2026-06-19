from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LandingConfig:
    operator: str
    domain: str
    url: str
    card_selectors: tuple[str, ...]
    title_selectors: tuple[str, ...]
    cta_selectors: tuple[str, ...]
    comment: str = ""


DEFAULT_TITLE_SELECTORS = (
    "h1",
    "h2",
    "h3",
    "h4",
    "[class*='title']",
    "[class*='name']",
    "[class*='tariff']",
)

MTS_TITLE_SELECTORS = (
    ".card-one__title [itemprop='name']",
    ".card-one__title h3.T_TITLE",
    ".card-one__title",
    "h3.T_TITLE",
    "[itemprop='name']",
    "[class*='title']",
    "[class*='name']",
    "[class*='tariff']",
)


MTS_CARD_SELECTORS = (
    ".card-one",
)

MTS_CTA_SELECTORS = (
    "button.button-red.card-one__button.button-mobile-application",
    "button.button-mobile-application",
    "button.card-one__button",
    "button.button-red.card-one__button",
    "a[href]",
)

BEELINE_CARD_SELECTORS = (
    ".tariff-block.uc-BLOCK-MOBILE-1 .card-block",
    ".card-block[class*=' T']",
    ".card-block__body",
    ".card-block",
)

BEELINE_TITLE_SELECTORS = (
    ".card-block__header [itemprop='name']",
    ".card-block__header .card-block__title",
    ".card-block__header",
    ".card-block__header-main [itemprop='name']",
    "div[itemprop='name'].card-block__title.T1_TITLE",
    ".card-block__header-main .card-block__title",
    "[itemprop='name'].card-block__title",
    ".card-block__title",
    "[itemprop='name']",
    "[class*='title']",
    "[class*='name']",
    "[class*='tariff']",
)

T2_CARD_SELECTORS = (
    ".card-new__description-block",
)

T2_TITLE_SELECTORS = (
    ".card-new__title [itemprop='name']",
    "[itemprop='name'].card-new__title",
    ".card-new__title",
    "h3.card-new__title",
    "h3.T1_TITLE",
    "[itemprop='name']",
    "[class*='title']",
    "[class*='name']",
    "[class*='tariff']",
)

T2_CTA_SELECTORS = (
    ".card-new__button.button-mobile-application",
    ".card-new__button",
    "button.button-mobile-application",
    "button",
    "a[href]",
)


LANDINGS: tuple[LandingConfig, ...] = (
    LandingConfig(
        operator="MTS",
        domain="mts-home-gpon.ru",
        url="https://mts-home-gpon.ru/moskva/mobilnaya-svyaz",
        card_selectors=MTS_CARD_SELECTORS,
        title_selectors=MTS_TITLE_SELECTORS,
        cta_selectors=MTS_CTA_SELECTORS,
        comment="MTS Moscow landing.",
    ),
    LandingConfig(
        operator="MTS",
        domain="mts-home-gpon.ru",
        url="https://mts-home-gpon.ru/sankt-peterburg/mobilnaya-svyaz",
        card_selectors=MTS_CARD_SELECTORS,
        title_selectors=MTS_TITLE_SELECTORS,
        cta_selectors=MTS_CTA_SELECTORS,
        comment="MTS Saint Petersburg landing.",
    ),
    LandingConfig(
        operator="MTS",
        domain="mts-home.online",
        url="https://mts-home.online/mobilnaya-svyaz",
        card_selectors=MTS_CARD_SELECTORS,
        title_selectors=MTS_TITLE_SELECTORS,
        cta_selectors=MTS_CTA_SELECTORS,
        comment="MTS landing without region prefix.",
    ),
    LandingConfig(
        operator="MTS",
        domain="sankt-peterburg.mts-home.online",
        url="https://sankt-peterburg.mts-home.online/mobilnaya-svyaz",
        card_selectors=MTS_CARD_SELECTORS,
        title_selectors=MTS_TITLE_SELECTORS,
        cta_selectors=MTS_CTA_SELECTORS,
        comment="MTS Saint Petersburg subdomain.",
    ),
    LandingConfig(
        operator="MTS",
        domain="mts-home-online.ru",
        url="https://mts-home-online.ru/moskva/mobilnaya-svyaz",
        card_selectors=MTS_CARD_SELECTORS,
        title_selectors=MTS_TITLE_SELECTORS,
        cta_selectors=MTS_CTA_SELECTORS,
        comment="MTS alt domain Moscow landing.",
    ),
    LandingConfig(
        operator="MTS",
        domain="mts-home-online.ru",
        url="https://mts-home-online.ru/sankt-peterburg/mobilnaya-svyaz",
        card_selectors=MTS_CARD_SELECTORS,
        title_selectors=MTS_TITLE_SELECTORS,
        cta_selectors=MTS_CTA_SELECTORS,
        comment="MTS alt domain Saint Petersburg landing.",
    ),
    LandingConfig(
        operator="Beeline",
        domain="beeline-internet.online",
        url="https://beeline-internet.online/tariffs-mobile",
        card_selectors=BEELINE_CARD_SELECTORS,
        title_selectors=BEELINE_TITLE_SELECTORS,
        cta_selectors=(
            ".card-block__button.button-mobile-application.popup-mobile-beeline",
            ".card-block__button.button-mobile-application",
            ".card-block__button",
            "a.card-block__button.button-mobile-application",
            "a[href]",
            "button",
        ),
        comment="Beeline main landing.",
    ),
    LandingConfig(
        operator="Beeline",
        domain="beeline-internet.online",
        url="https://beeline-internet.online/sankt-peterburg/tariffs-mobile",
        card_selectors=BEELINE_CARD_SELECTORS,
        title_selectors=BEELINE_TITLE_SELECTORS,
        cta_selectors=(
            ".card-block__button.button-mobile-application.popup-mobile-beeline",
            ".card-block__button.button-mobile-application",
            ".card-block__button",
            "a.card-block__button.button-mobile-application",
            "a[href]",
            "button",
        ),
        comment="Beeline Saint Petersburg landing.",
    ),
    LandingConfig(
        operator="Beeline",
        domain="moskva.beeline-ru.online",
        url="https://moskva.beeline-ru.online/tariffs-mobile",
        card_selectors=BEELINE_CARD_SELECTORS,
        title_selectors=BEELINE_TITLE_SELECTORS,
        cta_selectors=(
            ".card-block__button.button-mobile-application.popup-mobile-beeline",
            ".card-block__button.button-mobile-application",
            ".card-block__button",
            "a.card-block__button.button-mobile-application",
            "a[href]",
            "button",
        ),
        comment="Beeline Moscow subdomain landing.",
    ),
    LandingConfig(
        operator="Beeline",
        domain="beeline-ru.online",
        url="https://beeline-ru.online/tariffs-mobile",
        card_selectors=BEELINE_CARD_SELECTORS,
        title_selectors=BEELINE_TITLE_SELECTORS,
        cta_selectors=(
            ".card-block__button.button-mobile-application.popup-mobile-beeline",
            ".card-block__button.button-mobile-application",
            ".card-block__button",
            "a.card-block__button.button-mobile-application",
            "a[href]",
            "button",
        ),
        comment="Beeline RU landing.",
    ),
    LandingConfig(
        operator="Beeline",
        domain="online-beeline.ru",
        url="https://online-beeline.ru/tariffs-mobile",
        card_selectors=BEELINE_CARD_SELECTORS,
        title_selectors=BEELINE_TITLE_SELECTORS,
        cta_selectors=(
            ".card-block__button.button-mobile-application.popup-mobile-beeline",
            ".card-block__button.button-mobile-application",
            ".card-block__button",
            "a.card-block__button.button-mobile-application",
            "a[href]",
            "button",
        ),
        comment="Online Beeline main landing.",
    ),
    LandingConfig(
        operator="Beeline",
        domain="online-beeline.ru",
        url="https://online-beeline.ru/sankt-peterburg/tariffs-mobile",
        card_selectors=BEELINE_CARD_SELECTORS,
        title_selectors=BEELINE_TITLE_SELECTORS,
        cta_selectors=(
            ".card-block__button.button-mobile-application.popup-mobile-beeline",
            ".card-block__button.button-mobile-application",
            ".card-block__button",
            "a.card-block__button.button-mobile-application",
            "a[href]",
            "button",
        ),
        comment="Online Beeline Saint Petersburg landing.",
    ),
    LandingConfig(
        operator="T2",
        domain="t2-ru.online",
        url="https://t2-ru.online/mobilnaya-svyaz",
        card_selectors=T2_CARD_SELECTORS,
        title_selectors=T2_TITLE_SELECTORS,
        cta_selectors=T2_CTA_SELECTORS,
        comment="T2 main landing. Selectors reused from the reference project.",
    ),
    LandingConfig(
        operator="T2",
        domain="t2-ru.online",
        url="https://t2-ru.online/sankt-peterburg/mobilnaya-svyaz",
        card_selectors=T2_CARD_SELECTORS,
        title_selectors=T2_TITLE_SELECTORS,
        cta_selectors=T2_CTA_SELECTORS,
        comment="T2 Saint Petersburg landing. Selectors reused from the reference project.",
    ),
)
