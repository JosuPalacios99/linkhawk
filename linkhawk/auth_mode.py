"""Modo auth: TODAVIA EN DESARROLLO. login LinkedIn (voyager API interna via libreria
linkedin_api). Mas datos que dork mode pero riesgo de restriccion/ban de cuenta.
Usar cuenta desechable.

Requiere: pip install linkedin_api
Auth por user/pass, o por cookie li_at (recomendado, evita 2FA/challenge repetido).

Resuelve la organizacion a su URN de empresa (busqueda exacta) y filtra por
currentCompany, mucho mas preciso que buscar el nombre como keyword suelto.
Pagina manualmente con delay entre requests (la libreria no espera entre paginas).
"""
import random
import sys
import time

PAGE_SIZE = 49  # max soportado por voyager (linkedin_api.Linkedin._MAX_SEARCH_COUNT)
_NOISE_NAMES = {"linkedin member"}


def _get_client(username=None, password=None, li_at=None):
    from linkedin_api import Linkedin
    from linkedin_api.client import ChallengeException, UnauthorizedException

    try:
        if li_at:
            return Linkedin(username or "", password or "", cookies={"li_at": li_at}, refresh_cookies=False)
        if not username or not password:
            raise ValueError("necesita --username/--password o --li-at")
        return Linkedin(username, password)
    except ChallengeException:
        raise SystemExit(
            "[!] LinkedIn pidio verificacion (2FA/challenge). "
            "Loguea a mano en el navegador y usa --li-at en vez de user/pass."
        )
    except UnauthorizedException:
        raise SystemExit("[!] Credenciales invalidas o cookie de sesion rechazada.")


def _resolve_company_urn(client, org: str):
    """Busca la empresa y devuelve su urn_id para filtrar por currentCompany.
    None si no encuentra nada (cae a busqueda por keyword suelto, menos precisa)."""
    try:
        candidates = client.search_companies(keywords=[org])
    except Exception as e:
        print(f"[!] no se pudo resolver empresa '{org}': {e}", file=sys.stderr)
        return None
    if not candidates:
        return None
    org_l = org.strip().lower()
    for c in candidates:
        if (c.get("name") or "").strip().lower() == org_l:
            return c["urn_id"]
    return candidates[0]["urn_id"]  # mejor aproximacion disponible


def _extract_person(item: dict):
    name = (item.get("name") or "").strip()
    return {
        "name": name,
        "title": (item.get("jobtitle") or "").strip(),
        "url": "",  # la busqueda no devuelve public_id, ver resolve_urls
        "urn_id": item.get("urn_id", ""),
    }


def _resolve_url(client, urn_id, delay):
    """Un request extra por perfil para sacar el public_id -> URL /in/slug.
    Caro y con mas riesgo de rate-limit, por eso es opt-in (--resolve-urls)."""
    try:
        profile = client.get_profile(urn_id=urn_id)
        public_id = profile.get("public_id")
        time.sleep(delay + random.uniform(0, 0.5))
        return f"https://www.linkedin.com/in/{public_id}" if public_id else ""
    except Exception:
        return ""


def run(org: str, username=None, password=None, li_at=None, max_results=200, delay=1.5, resolve_urls=False):
    client = _get_client(username, password, li_at)

    company_urn = _resolve_company_urn(client, org)
    current_company = [company_urn] if company_urn else None
    if company_urn:
        print(f"[*] empresa resuelta -> urn {company_urn}", file=sys.stderr)
    else:
        print(f"[!] sin match exacto de empresa para '{org}', busco por keyword suelto (menos preciso)", file=sys.stderr)

    results = []
    seen = set()
    offset = 0
    while len(results) < max_results:
        try:
            batch = client.search_people(
                keyword_company=None if current_company else org,
                current_company=current_company,
                include_private_profiles=True,
                limit=PAGE_SIZE,
                offset=offset,
            )
        except Exception as e:
            print(f"[!] error en busqueda (offset={offset}): {e}", file=sys.stderr)
            break

        if not batch:
            break

        for item in batch:
            person = _extract_person(item)
            key = person["urn_id"] or person["name"]
            if not person["name"] or person["name"].lower() in _NOISE_NAMES or key in seen:
                continue
            seen.add(key)
            results.append(person)
            if len(results) >= max_results:
                break

        if len(batch) < PAGE_SIZE or len(results) >= max_results:
            break

        offset += PAGE_SIZE
        time.sleep(delay + random.uniform(0, 1))  # entre paginas, evita rate-limit/ban

    if resolve_urls:
        print(f"[*] resolviendo urls ({len(results)} requests extra)...", file=sys.stderr)
        for p in results:
            if p["urn_id"]:
                p["url"] = _resolve_url(client, p["urn_id"], delay)

    for p in results:
        p.pop("urn_id", None)
    return results[:max_results]
