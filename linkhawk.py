#!/usr/bin/env python3
"""
linkhawk.py - LinkedIn employee name/title enumeration + email generation.
Browser mode (real browser, headed or headless) and auth mode (login, voyager API).

Usage:
  # real browser, solve captcha by hand the first time
  python3 linkhawk.py browser -o "Acme Corp" -d acme.com --output out.csv

  # same but headless, reuses already-solved session cookies
  python3 linkhawk.py browser -o "Acme Corp" -d acme.com --headless --output out.csv

  # with login (more coverage, account risk)
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
    """part='email' -> full line name@domain. part='user' -> local-part only (before @)."""
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
    parser = argparse.ArgumentParser(description="LinkHawk: LinkedIn recon, names/titles + email permutations")
    sub = parser.add_subparsers(dest="mode", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-o", "--org", required=True, help="Organization name (e.g. 'Acme Corp')")
    common.add_argument("-d", "--domain", help="Domain to generate emails from (e.g. acme.com)")
    common.add_argument("--email-format", default=None, choices=list(FORMATS.keys()),
                         help="Email format to generate (without this or --all-formats, no email is generated)")
    common.add_argument("--all-formats", action="store_true", help="Generate all email permutations per row")
    common.add_argument("--output", default="linkhawk.csv", help="Output CSV file")
    common.add_argument("--emails-out", default=None, help="Plain txt file, emails only (one per line), requires --domain")
    common.add_argument("--usernames-out", default=None,
                         help="Plain txt file, email local-part only (no domain), requires --domain")
    common.add_argument("--delay", type=float, default=2.0, help="Base delay between requests (sec)")

    p_auth = sub.add_parser("auth", parents=[common], help="Mode with LinkedIn login (internal voyager API)")
    p_auth.add_argument("--username", help="LinkedIn account email (if not using --li-at)")
    p_auth.add_argument("--password", help="LinkedIn account password (if not using --li-at)")
    p_auth.add_argument("--li-at", help="li_at session cookie (preferred over user/pass)")
    p_auth.add_argument("--max-results", type=int, default=200, help="Max profiles to retrieve")
    p_auth.add_argument("--resolve-urls", action="store_true",
                         help="Fetch the profile URL (1 extra request per person, slower and more rate-limit risk)")

    p_browser = sub.add_parser(
        "browser", parents=[common],
        help="Real browser mode (undetected-chromedriver), solve captcha by hand",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            '  python3 linkhawk.py browser -o "ECORP" -d ecorp.com -e bing --pages 5 --headless --output out.csv\n'
        ),
    )
    p_browser.add_argument("-e", "--engine", default="all", choices=["bing", "duckduckgo", "google", "all"],
                            help="Search engine, 'all' runs all 3 (default: all)")
    p_browser.add_argument("--pages", type=int, default=10, help="Result pages to walk (default: 10)")
    p_browser.add_argument("--extra", default="", help="Extra term to narrow the search (e.g. city)")
    p_browser.add_argument("--proxy", default="", help="Proxy host:port for the browser (optional)")
    p_browser.add_argument("--headless", action="store_true",
                            help="No visible window (can't solve a captcha if one shows up)")

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
            parser.error("auth mode needs --li-at or --username/--password")
        print("[!] auth mode: still under development, may fail or give incomplete results", file=sys.stderr)
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
    print(f"[*] {len(people)} unique profiles found", file=sys.stderr)

    write_csv(args.output, people, args.domain, args.email_format, args.all_formats)
    print(f"[+] saved to {args.output}", file=sys.stderr)

    if args.emails_out or args.usernames_out:
        if not args.domain:
            parser.error("--emails-out/--usernames-out require --domain")
    if args.emails_out:
        write_plain(args.emails_out, people, args.domain, args.email_format, "email")
        print(f"[+] saved to {args.emails_out}", file=sys.stderr)
    if args.usernames_out:
        write_plain(args.usernames_out, people, args.domain, args.email_format, "user")
        print(f"[+] saved to {args.usernames_out}", file=sys.stderr)


if __name__ == "__main__":
    main()
