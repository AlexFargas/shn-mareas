#!/usr/bin/env python3
"""
Lee las alturas medidas y el pronóstico mareológico del Servicio de Hidrografía Naval (SHN)
para San Fernando y escribe marea.json. Solo usa la biblioteca estándar de Python.
Formato de salida compatible con la app wind-buddy-ba (TideData).
"""
import json, re, sys, datetime, urllib.request

CSV_URL = "https://www.hidro.gob.ar/oceanografia/AlturasHorarias.asp?export=csv"
FORECAST_URL = "https://www.hidro.gob.ar/oceanografia/pronostico.asp"
STATION = "San Fernando"
UA = {"User-Agent": "Mozilla/5.0 (shn-mareas)"}


def fetch_text(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as res:
        ctype = res.headers.get("Content-Type", "")
        m = re.search(r"charset=([\w-]+)", ctype, re.I)
        charset = m.group(1) if m else "utf-8"
        raw = res.read()
    try:
        return raw.decode(charset)
    except (LookupError, UnicodeDecodeError):
        return raw.decode("utf-8", "replace")


def to_iso(d, t):
    # "18/10/2026" + "09:45", hora de Buenos Aires (UTC-3, sin horario de verano)
    dd, mm, yyyy = d.split("/")
    hh, mi = t.split(":")
    return f"{yyyy}-{mm.zfill(2)}-{dd.zfill(2)}T{hh.zfill(2)}:{mi}:00-03:00"


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", s).strip()


def observed():
    lines = [l for l in fetch_text(CSV_URL).splitlines() if l.strip()]
    header = [h.strip().lower() for h in lines[0].split(";")]
    if STATION.lower() not in header:
        raise RuntimeError(f"Columna {STATION} no encontrada en el CSV del SHN")
    col = header.index(STATION.lower())
    out = []
    for line in lines[1:]:
        cells = line.split(";")
        parts = cells[0].strip().split()
        if len(parts) != 2 or col >= len(cells):
            continue
        try:
            h = float(cells[col].replace(",", "."))
        except ValueError:
            continue
        out.append({"t": to_iso(parts[0], parts[1]), "h": h})
    out.sort(key=lambda x: x["t"])  # más viejo primero
    return out[-48:]  # últimas 48 horas


def forecast():
    html = fetch_text(FORECAST_URL)
    mi = re.search(r"RIO DE LA PLATA INTERIOR", html, re.I)
    me = re.search(r"RIO DE LA PLATA EXTERIOR", html, re.I)
    if not mi:
        raise RuntimeError("Formato del pronóstico SHN no reconocido")
    section = html[mi.start(): me.start() if me and me.start() > mi.start() else None]

    m = re.search(r"<strong>([\s\S]*?)</strong>", section, re.I)
    correction = clean(m.group(1)) if m else ""
    m = re.search(r"VALIDO DESDE[\s\S]*?</p>", html, re.I)
    validity = clean(m.group(0)) if m else ""

    extremes, place = [], ""
    for tr in re.findall(r"<tr>[\s\S]*?</tr>", section, re.I):
        cells = [clean(c) for c in re.findall(r"<td[^>]*>([\s\S]*?)</td>", tr, re.I)]
        if len(cells) < 5:
            continue
        if cells[0]:
            place = cells[0]
        if not re.search("SAN FERNANDO", place, re.I):
            continue
        if not re.fullmatch(r"\d{1,2}:\d{2}", cells[2]):
            continue
        try:
            h = float(cells[3].replace(",", "."))
        except ValueError:
            continue
        extremes.append({
            "type": "pleamar" if cells[1].upper().startswith("PLEA") else "bajamar",
            "t": to_iso(cells[4], cells[2]),
            "h": h,
        })

    m = re.search(
        r"PERSPECTIVAS VALIDAS PARA EL DIA ([^<:]+)[\s\S]*?Rio de la Plata Interior</h4>\s*<p>([\s\S]*?)<(?:/p|p|h4|div)",
        html, re.I)
    perspective = {"day": clean(m.group(1)), "text": clean(m.group(2))} if m else None
    return {"validity": validity, "correction": correction, "extremes": extremes, "perspective": perspective}


def main(path="marea.json"):
    errors, obs, fc = {}, [], None
    try:
        obs = observed()
    except Exception as e:  # noqa: BLE001
        errors["observed"] = str(e)
    try:
        fc = forecast()
    except Exception as e:  # noqa: BLE001
        errors["forecast"] = str(e)

    # Si fallan ambas fuentes, conservar el archivo anterior en lugar de pisarlo con nada
    if not obs and fc is None:
        print("SHN no respondió; se conserva el marea.json anterior:", errors, file=sys.stderr)
        return 0

    data = {
        "station": STATION,
        "observed": obs,
        "forecast": fc,
        "errors": errors,
        "fetchedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"OK: {len(obs)} alturas, {len(fc['extremes']) if fc else 0} extremos, errores={errors}")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
