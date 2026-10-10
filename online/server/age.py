"""1.8 GDD v3.1: bramka wiekowa (RODO art. 8 — w Polsce 16 lat) i zgoda opiekuna."""
import datetime
import hashlib
import logging
import os
import re
import secrets

MIN_AGE = 12          # PEGI 12 — młodsi: odmowa rejestracji
CONSENT_AGE = 16      # RODO art. 8 (PL): poniżej — zgoda opiekuna przed przetwarzaniem danych
TOKEN_DAYS = 7        # ważność tokenu; po terminie konto pending jest usuwane
EMAIL_RE = re.compile(r'^[^@\s]{1,64}@[^@\s]{1,190}\.[a-z]{2,24}$', re.I)


def require_birth_date():
    # Faza B (frontend gotowy) włączy CITY_REQUIRE_BIRTH_DATE=1
    return os.getenv('CITY_REQUIRE_BIRTH_DATE', '0') == '1'


def today_from_ms(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).date()


def parse_birth(text, today):
    # Zwraca date albo rzuca ValueError z komunikatem po polsku
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', text or ''):
        raise ValueError('Data urodzenia w formacie RRRR-MM-DD.')
    try:
        birth = datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError('Nieprawidłowa data urodzenia.')
    if birth > today:
        raise ValueError('Data urodzenia nie może być z przyszłości.')
    if today.year - birth.year > 120:
        raise ValueError('Nieprawidłowa data urodzenia.')
    return birth


def age_on(birth, today):
    # Pełne lata (urodzeni 29 lutego: urodziny 1 marca w latach nieprzestępnych)
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def new_token():
    token = secrets.token_urlsafe(32)
    return token, token_hash(token)


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class Mailer:
    """Interfejs wysyłki. Dev-stub: loguje token zamiast wysyłać (podmiana na SMTP/usługę przed launchem)."""

    def send_guardian(self, email, child_login, token):
        logging.getLogger('city.guardian').warning('[DEV-STUB] zgoda opiekuna dla %s → %s: token %s', child_login, email, token)
