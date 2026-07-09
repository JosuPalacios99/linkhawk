"""Generación de permutaciones de email a partir de nombre+apellido y dominio."""
import re
import unicodedata


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def clean_token(s: str) -> str:
    s = strip_accents(s).lower()
    return re.sub(r"[^a-z0-9]", "", s)


def split_name(full_name: str):
    """Devuelve (first, last) best-effort. Convencion es. (nombre + apellido1 + apellido2):
    primer token = first, segundo token = last (primer apellido, no el segundo)."""
    parts = [p for p in re.split(r"\s+", full_name.strip()) if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


FORMATS = {
    "first.last": "{f}.{l}@{d}",
    "firstlast": "{f}{l}@{d}",
    "first_last": "{f}_{l}@{d}",
    "flast": "{f0}{l}@{d}",
    "first.l": "{f}.{l0}@{d}",
    "last.first": "{l}.{f}@{d}",
    "lastf": "{l}{f0}@{d}",
    "first": "{f}@{d}",
}


def generate_email(full_name: str, domain: str, fmt: str) -> str:
    first, last = split_name(full_name)
    f, l = clean_token(first), clean_token(last)
    f0 = f[:1]
    l0 = l[:1]
    template = FORMATS.get(fmt)
    if not template or not f:
        return ""
    if not l and "{l}" in template:
        return ""
    return template.format(f=f, l=l, f0=f0, l0=l0, d=domain)


def generate_all(full_name: str, domain: str):
    return {fmt: generate_email(full_name, domain, fmt) for fmt in FORMATS}
