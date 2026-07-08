<div align="center">

# LinkHawk

**Employee recon via LinkedIn: name + title by dorking search engines
(or direct login), plus email permutation generation from a domain.**

<br>

![Python](https://img.shields.io/badge/python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Mode](https://img.shields.io/badge/mode-browser%20%7C%20auth-1f6feb?style=for-the-badge)
![Engines](https://img.shields.io/badge/engines-bing%20%C2%B7%20duckduckgo%20%C2%B7%20google-444?style=for-the-badge)
![Output](https://img.shields.io/badge/output-CSV%20%2F%20TXT-5b2c6f?style=for-the-badge)

</div>

<br>

<table>
<tr>
<td width="50%" valign="top">

### What it does

- **Browser mode** — real Chrome (`undetected-chromedriver`),
  dorking `site:linkedin.com/in/` against Bing/DuckDuckGo/Google.
- **Email generation** — permutations (`first.last`,
  `flast`, etc.) from first+last name and a domain.

</td>
<td width="50%" valign="top">

### How it gets in

- **No login** — real browser avoids the fingerprint that
  blocks plain `requests`/`curl`; solve the captcha by hand
  once, then reuse the session.
- **With login (experimental)** — internal voyager API
  via `linkedin_api`, more coverage, more account risk.

</td>
</tr>
</table>

<div align="center">

[Structure](#structure) &nbsp;·&nbsp;
[Requirements](#requirements) &nbsp;·&nbsp;
[Install](#install) &nbsp;·&nbsp;
[Browser mode](#browser-mode--recommended) &nbsp;·&nbsp;
[Auth mode](#auth-mode) &nbsp;·&nbsp;
[Output](#output) &nbsp;·&nbsp;
[Email formats](#supported-email-formats)

</div>

---

## Structure

```text
linkhawk.py       # entrypoint, standalone script
linkhawk/         # package: auth_mode.py, browser_mode.py, emails.py
```

---

## Requirements

```text
Python 3.8+
Chrome/Chromium installed (used by browser mode)
```

```text
beautifulsoup4
linkedin_api
selenium
undetected-chromedriver
setuptools
```

---

## Install

```bash
# clone / enter the repo
cd linkhawk

# create venv (at repo root, see .gitignore: bin/ lib/ pyvenv.cfg)
python3 -m venv .

# activate venv
source bin/activate       # Linux/macOS
Scripts\activate           # Windows (cmd/PowerShell)

# install dependencies inside the venv
pip install -r requirements.txt
```

To leave the venv: `deactivate`. On later runs, just repeat
`source bin/activate` before running `linkhawk.py`.

---

## Browser mode — recommended

Opens a real Chrome (via `undetected-chromedriver`) and fires dorks like
`site:linkedin.com/in/ "Org"` against Bing, DuckDuckGo and/or Google, parsing
the results. Being a real browser avoids the fingerprint that blocks plain
`requests`/`curl`.

```bash
# first run: visible window, in case a captcha needs solving by hand
python3 linkhawk.py browser -o "Acme Corp" -d acme.com -e bing --pages 5 --output out.csv

# later runs: headless, reuses the already-solved session/cookies
python3 linkhawk.py browser -o "Acme Corp" -d acme.com -e bing --pages 10 --headless --output out.csv
```

> [!NOTE]
> The Chrome profile lives in `~/.linkedin_recon_chrome_profile` and keeps
> cookies between runs. If the engine returns a captcha or challenge
> ("verify you are human", etc.), execution pauses and asks you to solve it
> by hand in the window before continuing.

### How it works

1. Builds the dork query (`--extra` can narrow it further, e.g. a city).
2. Walks `--pages` pages of results per engine (`--engine`).
3. Parses each result's `<title>` (`Name - Title - Company | LinkedIn`)
   to extract name and title; discards names that don't look like real names.
4. If the engine returns a captcha or challenge, pauses and asks you to solve it by hand.

### Engines (`-e/--engine`)

| Value | What it does |
|---|---|
| `bing` | Bing only |
| `duckduckgo` | DuckDuckGo only (HTML, no JS) |
| `google` | Google only (fastest to demand a captcha) |
| `all` | All three in the same pass — **default** |

### Persistent session and `--headless`

The first time, run **without** `--headless` so you can solve the captcha if
it shows up; while that session stays alive, later runs with `--headless`
shouldn't ask for it again. If the session expires or the fingerprint gets
banned, run again without `--headless` to solve it.

### Useful flags

| Flag | What for |
|---|---|
| `--pages N` | Result pages per engine (default 10) |
| `--extra "term"` | Narrows the search (city, department, etc.) |
| `--proxy host:port` | Routes browser traffic through a proxy |
| `--delay N` | Base delay in seconds between requests |
| `--headless` | No visible window (can't solve a captcha if one shows up) |

---

## Auth mode

> [!WARNING]
> Still under development. Direct login against LinkedIn's internal API
> (voyager, via the `linkedin_api` library). In theory it gives more coverage
> than dork mode since it searches by company inside LinkedIn instead of
> depending on what search engines index, but **it's experimental**: it can
> fail, give incomplete results, or fail to resolve the profile URL. Also,
> logging in with a real account carries restriction/challenge/ban risk —
> use a throwaway account, never your personal one.

```bash
python3 linkhawk.py auth -o "Acme Corp" -d acme.com --li-at <cookie_li_at> --output out.csv
```

The `li_at` cookie is grabbed from an already-logged-in browser
(DevTools → Application → Cookies → linkedin.com). Preferable over passing
a plaintext username/password, which triggers 2FA/checkpoint more easily.

---

## Output

Each run auto-creates `output/<org_slug>/` and saves the CSV there
(`--output`), plus, if requested, the plain `--emails-out` / `--usernames-out`
files (one per line, require `--domain`; `--usernames-out` is just the
local-part before the `@`).

## Supported email formats

`first.last` `firstlast` `first_last` `flast` `first.l` `last.first` `lastf` `first`

Without `--email-format` or `--all-formats`, the CSV carries no email column.
`--all-formats` generates all permutations as columns.

---

<div align="center">
<sub>For authorized recon only — stay within your engagement scope.</sub>
</div>
