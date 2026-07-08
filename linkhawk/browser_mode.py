"""Modo browser: navegador real (undetected-chromedriver) para saltar captcha/soft-block
de bing/duckduckgo/google. Primera vez pide resolver captcha a mano en la ventana; luego
reusa perfil persistente (~/.linkedin_recon_chrome_profile) asi las siguientes corridas
no vuelven a pedir captcha mientras la cookie de sesion siga viva.
"""
import re
import time
import random
import shutil
import subprocess
import urllib.parse
from pathlib import Path

import undetected_chromedriver as uc
from bs4 import BeautifulSoup

# titulo tipico: "Nombre Apellido - Puesto - Empresa | LinkedIn"
TITLE_SPLIT_RE = re.compile(r"\s*[-|–]\s*")


def _parse_title(raw_title: str):
    title = re.sub(r"\s*\|\s*LinkedIn\s*$", "", raw_title.strip())
    parts = TITLE_SPLIT_RE.split(title)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return None, None
    name = parts[0]
    puesto = parts[1] if len(parts) > 1 else ""
    return name, puesto


def _valid_name(name: str) -> bool:
    if not name:
        return False
    if not re.match(r"^[A-Za-zÀ-ÿ' .-]+$", name):
        return False
    return 1 <= len(name.split()) <= 5


def _installed_chrome_major():
    """undetected-chromedriver necesita el major version exacto del Chrome instalado
    para bajar el chromedriver que hace match; si no, SessionNotCreatedException."""
    for binname in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(binname)
        if not path:
            continue
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10).stdout
        m = re.search(r"(\d+)\.", out)
        if m:
            return int(m.group(1))
    return None

PROFILE_DIR = str(Path.home() / ".linkedin_recon_chrome_profile")

CHALLENGE_MARKERS = [
    "solve the challenge",
    "unusual traffic",
    "select all squares",
    "verify you are human",
    "detected unusual activity",
    "one last step",
]

ENGINE_URLS = {
    "bing": lambda q, page: f"https://www.bing.com/search?q={q}&first={page * 10 + 1}",
    "duckduckgo": lambda q, page: f"https://duckduckgo.com/html/?q={q}&s={page * 30}",
    "google": lambda q, page: f"https://www.google.com/search?q={q}&start={page * 10}",
}


def _is_challenge(html: str) -> bool:
    low = html.lower()
    return any(m in low for m in CHALLENGE_MARKERS)


def _extract(engine, soup):
    results = []
    if engine == "google":
        anchors = soup.select("a h3")
        for h3 in anchors:
            a = h3.find_parent("a")
            if not a:
                continue
            href = a.get("href", "")
            if "linkedin.com/in" not in href:
                continue
            name, title = _parse_title(h3.get_text(" ", strip=True))
            if _valid_name(name):
                results.append({"name": name, "title": title, "url": href})
        return results

    sel = "li.b_algo h2 a" if engine == "bing" else "a.result__a"
    for a in soup.select(sel):
        href = a.get("href", "")
        if "linkedin.com/in" not in href:
            continue
        name, title = _parse_title(a.get_text(" ", strip=True))
        if _valid_name(name):
            results.append({"name": name, "title": title, "url": href})
    return results


def run(org: str, engine: str, max_pages: int, delay: float, extra: str = "", headless: bool = False, proxy: str = ""):
    query = f'site:linkedin.com/in/ "{org}"'
    if extra:
        query += f' "{extra}"'
    q = urllib.parse.quote(query)

    engines = list(ENGINE_URLS.keys()) if engine == "all" else [engine]

    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    if proxy:
        options.add_argument(f"--proxy-server={proxy}")

    driver = uc.Chrome(options=options, user_data_dir=PROFILE_DIR, version_main=_installed_chrome_major())

    all_results = []
    try:
        for eng in engines:
            print(f"[*] browser engine={eng}")
            for page in range(max_pages):
                url = ENGINE_URLS[eng](q, page)
                driver.get(url)
                time.sleep(2)
                if _is_challenge(driver.page_source):
                    input(
                        f"[!] Captcha/challenge en {eng}. Resuelvelo en la ventana del navegador "
                        "y pulsa Enter aqui para continuar..."
                    )
                    driver.get(url)
                    time.sleep(2)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                page_results = _extract(eng, soup)
                if not page_results:
                    break
                all_results += page_results
                time.sleep(delay + random.uniform(0.5, 1.5))
    finally:
        driver.quit()

    return all_results
