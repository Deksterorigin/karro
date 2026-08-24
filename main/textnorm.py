import re
import unicodedata

_APOSTROPHE_MAP = str.maketrans({
    '\u2019': "'",
    '\u02bc': "'",
    '\u02bb': "'",
    '`': "'",
    '\u00b4': "'",
})
_YE_MAP = str.maketrans({'\u0451': '\u0435'})
_WHITESPACE_RE = re.compile(r'\s+')


def fold_text(value):
    if value is None:
        return ''
    text = unicodedata.normalize('NFKC', str(value)).casefold()
    text = text.translate(_YE_MAP).translate(_APOSTROPHE_MAP)
    return _WHITESPACE_RE.sub(' ', text).strip()


def tokenize(value, max_tokens=10):
    if not value:
        return []
    return fold_text(value).split(' ')[:max_tokens]


def escape_like(text):
    return (
        str(text)
        .replace('\\', '\\\\')
        .replace('%', '\\%')
        .replace('_', '\\_')
    )
