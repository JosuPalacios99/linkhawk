# LinkHawk

Recon de empleados via LinkedIn: nombre + puesto por dorking en buscadores (o login directo),
mas generacion de permutaciones de email a partir de un dominio.

## Estructura

```
linkhawk.py       # entrypoint, unico script suelto
linkhawk/         # paquete: auth_mode.py, browser_mode.py, emails.py
```

## Requisitos

- Python 3.8+
- Chrome/Chromium instalado (lo usa el modo browser)

## Instalar

```bash
# clonar / entrar al repo
cd linkhawk

# crear venv (en la raiz del repo, ver .gitignore: bin/ lib/ pyvenv.cfg)
python3 -m venv .

# activar venv
source bin/activate       # Linux/macOS
Scripts\activate           # Windows (cmd/PowerShell)

# instalar dependencias dentro del venv
pip install -r requirements.txt
```

Para salir del venv: `deactivate`. En corridas siguientes, solo hace falta
repetir el `source bin/activate` antes de correr `linkhawk.py`.

---

## Modo browser — recomendado

Abre un Chrome real (via `undetected-chromedriver`) y lanza dorks del tipo
`site:linkedin.com/in/ "Org"` contra Bing, DuckDuckGo y/o Google, parseando
los resultados. Al ser un navegador real evita el fingerprint que bloquea a
`requests`/`curl` de entrada.

```bash
# primera vez: ventana visible, por si sale un captcha que resolver a mano
python3 linkhawk.py browser -o "Acme Corp" -d acme.com -e bing --pages 5 --output out.csv

# siguientes corridas: sin ventana, reusa la sesion/cookies ya resueltas
python3 linkhawk.py browser -o "Acme Corp" -d acme.com -e bing --pages 10 --headless --output out.csv
```

### Como funciona

1. Arma la query dork (`--extra` la puede acotar mas, ej. una ciudad).
2. Recorre `--pages` paginas de resultados por cada motor (`--engine`).
3. Parsea el `<title>` de cada resultado (`Nombre - Puesto - Empresa | LinkedIn`)
   para sacar nombre y puesto; descarta nombres que no pintan como nombres reales.
4. Si el motor devuelve un captcha o challenge ("verify you are human", etc.),
   la ejecucion se pausa y pide resolverlo a mano en la ventana antes de seguir.

### Motores (`-e/--engine`)

| Valor | Que hace |
|---|---|
| `bing` | Solo Bing |
| `duckduckgo` | Solo DuckDuckGo (HTML, sin JS) |
| `google` | Solo Google (el que mas rapido pide captcha) |
| `all` | Los tres en la misma pasada — **default** |

### Sesion persistente y `--headless`

El perfil de Chrome vive en `~/.linkedin_recon_chrome_profile` y guarda cookies
entre corridas. La primera vez, corre **sin** `--headless` para poder resolver
el captcha si aparece; mientras esa sesion siga viva, las siguientes corridas
con `--headless` no deberian volver a pedirlo. Si la sesion expira o banean el
fingerprint, corre de nuevo sin `--headless` para resolverlo.

### Flags utiles

| Flag | Para que |
|---|---|
| `--pages N` | Paginas de resultados por motor (default 10) |
| `--extra "termino"` | Acota la busqueda (ciudad, departamento, etc.) |
| `--proxy host:port` | Trafico del navegador por proxy |
| `--delay N` | Delay base en segundos entre requests |
| `--headless` | Sin ventana visible (no podras resolver captcha si sale uno) |

---

## Modo auth — ⚠️ todavia en desarrollo

Login directo contra la API interna de LinkedIn (voyager, via libreria
`linkedin_api`). En teoria da mas cobertura que el dork mode porque busca por
empresa dentro de LinkedIn en vez de depender de lo que indexen los buscadores,
pero **es experimental**: puede fallar, dar resultados incompletos, o no
resolver bien la URL del perfil. Ademas login con cuenta real conlleva riesgo
de restriccion/challenge/ban — usar una cuenta desechable, nunca la personal.

```bash
python3 linkhawk.py auth -o "Acme Corp" -d acme.com --li-at <cookie_li_at> --output out.csv
```

La cookie `li_at` se saca del navegador ya logueado
(DevTools → Application → Cookies → linkedin.com). Preferible sobre pasar
usuario/contraseña en claro, que dispara 2FA/checkpoint mas facil.

---

## Output

Cada corrida crea `output/<org_slug>/` automatico y guarda ahi el CSV
(`--output`) y, si se piden, los planos `--emails-out` / `--usernames-out`
(uno por linea, requieren `--domain`; `--usernames-out` es solo el
local-part antes de la `@`).

## Formatos de email soportados

`first.last` `firstlast` `first_last` `flast` `first.l` `last.first` `lastf` `first`

Sin `--email-format` ni `--all-formats`, el CSV no lleva columna email.
`--all-formats` genera todas las permutaciones como columnas.
