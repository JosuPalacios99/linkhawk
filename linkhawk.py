#!/usr/bin/env python3
"""
linkhawk.py - enumeracion nombre/puesto de empleados via LinkedIn + generacion emails.
Modo browser (navegador real, headed o headless) y modo auth (login, voyager API).

Uso:
  # navegador real, resuelve captcha a mano la primera vez
  python3 linkhawk.py browser -o "Acme Corp" -d acme.com --output out.csv

  # mismo pero sin ventana, reusa cookies de sesion ya resuelta
  python3 linkhawk.py browser -o "Acme Corp" -d acme.com --headless --output out.csv

  # con login (mas cobertura, riesgo cuenta)
  python3 linkhawk.py auth -o "Acme Corp" -d acme.com --li-at <cookie_li_at> --output out.csv
"""
import argparse
import csv
import os
import re
import sys

from linkhawk import auth_mode
from linkhawk.emails import generate_all, FORMATS


def slugify(org: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", org.strip().lower()).strip("_")
    return s or "org"


def write_csv(path, people, domain, email_format, all_formats):
    fieldnames = ["name", "title", "url"]
    want_email = domain and (all_formats or email_format)
    if want_email:
        fieldnames += list(FORMATS.keys()) if all_formats else ["email"]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in people:
            row = {"name": p["name"], "title": p.get("title", ""), "url": p.get("url", "")}
            if want_email:
                if all_formats:
                    row.update(generate_all(p["name"], domain))
                else:
                    row["email"] = generate_all(p["name"], domain).get(email_format, "")
            writer.writerow(row)


def write_plain(path, people, domain, email_format, part):
    """part='email' -> linea completa nombre@dominio. part='user' -> solo local-part (antes de @)."""
    fmt = email_format or "first.last"
    seen = set()
    with open(path, "w", encoding="utf-8") as f:
        for p in people:
            email = generate_all(p["name"], domain).get(fmt, "")
            if not email:
                continue
            value = email if part == "email" else email.split("@", 1)[0]
            if value in seen:
                continue
            seen.add(value)
            f.write(value + "\n")


def dedup(people):
    seen = set()
    out = []
    for p in people:
        key = (p["name"].lower(), p.get("url", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def main():
    parser = argparse.ArgumentParser(description="LinkHawk: LinkedIn recon, nombres/puestos + email permutations")
    sub = parser.add_subparsers(dest="mode", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-o", "--org", required=True, help="Nombre de la organizacion (ej. 'Acme Corp')")
    common.add_argument("-d", "--domain", help="Dominio para generar emails (ej. acme.com)")
    common.add_argument("--email-format", default=None, choices=list(FORMATS.keys()),
                         help="Formato de email a generar (sin esto y sin --all-formats, no se genera email)")
    common.add_argument("--all-formats", action="store_true", help="Genera todas las permutaciones de email por fila")
    common.add_argument("--output", default="linkhawk.csv", help="Fichero CSV de salida")
    common.add_argument("--emails-out", default=None, help="Fichero txt solo emails (uno por linea), requiere --domain")
    common.add_argument("--usernames-out", default=None,
                         help="Fichero txt solo local-part del email (usuario sin dominio), requiere --domain")
    common.add_argument("--delay", type=float, default=2.0, help="Delay base entre requests (seg)")

    p_auth = sub.add_parser("auth", parents=[common], help="Modo con login LinkedIn (voyager API interna)")
    p_auth.add_argument("--username", help="Email cuenta LinkedIn (si no usas --li-at)")
    p_auth.add_argument("--password", help="Password cuenta LinkedIn (si no usas --li-at)")
    p_auth.add_argument("--li-at", help="Cookie de sesion li_at (recomendado sobre user/pass)")
    p_auth.add_argument("--max-results", type=int, default=200, help="Maximo de perfiles a recuperar")
    p_auth.add_argument("--resolve-urls", action="store_true",
                         help="Saca la URL de perfil (1 request extra por persona, mas lento y mas riesgo de rate-limit)")

    p_browser = sub.add_parser(
        "browser", parents=[common],
        help="Modo navegador real (undetected-chromedriver), salta captcha a mano",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplo:\n"
            '  python3 linkhawk.py browser -o "ECORP" -d ecorp.com -e bing --pages 5 --headless --output out.csv\n'
        ),
    )
    p_browser.add_argument("-e", "--engine", default="all", choices=["bing", "duckduckgo", "google", "all"],
                            help="Motor de busqueda, 'all' corre los 3 (default: all)")
    p_browser.add_argument("--pages", type=int, default=10, help="Paginas de resultados a recorrer (default: 10)")
    p_browser.add_argument("--extra", default="", help="Termino extra para acotar busqueda (ej. ciudad)")
    p_browser.add_argument("--proxy", default="", help="Proxy host:port para el navegador (opcional)")
    p_browser.add_argument("--headless", action="store_true",
                            help="Sin ventana visible (no puedes resolver captcha si sale uno)")

    args = parser.parse_args()

    org_dir = os.path.join("output", slugify(args.org))
    os.makedirs(org_dir, exist_ok=True)
    args.output = os.path.join(org_dir, os.path.basename(args.output))
    if args.emails_out:
        args.emails_out = os.path.join(org_dir, os.path.basename(args.emails_out))
    if args.usernames_out:
        args.usernames_out = os.path.join(org_dir, os.path.basename(args.usernames_out))

    if args.mode == "browser":
        from linkhawk import browser_mode
        print(f"[*] browser mode | engine={args.engine} org='{args.org}' pages={args.pages}", file=sys.stderr)
        people = browser_mode.run(args.org, args.engine, args.pages, args.delay, args.extra, args.headless, args.proxy)
    else:
        if not args.li_at and not (args.username and args.password):
            parser.error("auth mode necesita --li-at o --username/--password")
        print("[!] auth mode: todavia en desarrollo, puede fallar o dar resultados incompletos", file=sys.stderr)
        print(f"[*] auth mode | org='{args.org}'", file=sys.stderr)
        people = auth_mode.run(
            args.org,
            username=args.username,
            password=args.password,
            li_at=args.li_at,
            max_results=args.max_results,
            delay=args.delay,
            resolve_urls=args.resolve_urls,
        )

    people = dedup(people)
    print(f"[*] {len(people)} perfiles unicos encontrados", file=sys.stderr)

    write_csv(args.output, people, args.domain, args.email_format, args.all_formats)
    print(f"[+] guardado en {args.output}", file=sys.stderr)

    if args.emails_out or args.usernames_out:
        if not args.domain:
            parser.error("--emails-out/--usernames-out necesitan --domain")
    if args.emails_out:
        write_plain(args.emails_out, people, args.domain, args.email_format, "email")
        print(f"[+] guardado en {args.emails_out}", file=sys.stderr)
    if args.usernames_out:
        write_plain(args.usernames_out, people, args.domain, args.email_format, "user")
        print(f"[+] guardado en {args.usernames_out}", file=sys.stderr)


if __name__ == "__main__":
    main()
