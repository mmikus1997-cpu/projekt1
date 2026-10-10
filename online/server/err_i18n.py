"""8.5 GDD v3.1: tłumaczenie komunikatów błędów 4xx (409/422/403/401...) na en/de/fr.
Komunikaty w kodzie zostają po polsku (kompatybilność wstecz); tłumaczenie odbywa się
w handlerze wyjątków na podstawie słownika fragmentów (i18n/errors.json, klucz = tekst pl).
Jedno przejście regexem, najdłuższe fragmenty najpierw — liczby i nazwy wstawiane dynamicznie zostają."""
import json, re, os

_D = json.load(open(os.path.join(os.path.dirname(__file__), 'i18n', 'errors.json'), encoding='utf-8'))
_MAP = {l: dict(zip(_D['pl'], _D[l])) for l in ('en', 'de', 'fr')}
_RX = re.compile('|'.join(re.escape(s) for s in sorted(set(_D['pl']), key=len, reverse=True)))


def translate(text, lang):
    """Zwraca komunikat w języku lang; dla pl lub nie-tekstu bez zmian."""
    if lang not in _MAP or not isinstance(text, str):
        return text
    m = _MAP[lang]
    return _RX.sub(lambda g: m.get(g.group(0), g.group(0)), text)
