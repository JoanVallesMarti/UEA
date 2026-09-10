#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Actualitzador nocturn de l'app U.E. Aldeana.

Consulta la Federacio Catalana de Futbol (club 3085) i reescriu, dins d'index.html,
els blocs de dades marcats com AUTO-DATA:
  MATCHES · TEAM_RESULTS · T1_RESULTS · TEAM_TABLE · T1_TABLE
  FIXTURES_UPDATED · T1_TABLE_UPDATED

No toca res mes. Si la sortida no passa les comprovacions (node --check, marcadors,
mida raonable, nota del mister intacta) NO escriu res i acaba amb error.

L'executa .github/workflows/update.yml cada nit. Tambe es pot llancar a ma:
    python scripts/update.py
"""
import base64, datetime, io, json, os, re, subprocess, sys, tempfile, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "index.html")
TODAY = datetime.date.today().isoformat()
SEASON_START = "2026-07-01"
CLUB = "U.E. Aldeana"

# id : (codi FCF, nom, etiqueta competicio, grupId classificacio o None)
TEAMS = {
    "primer":    ("44373",    "U.E. Aldeana", "Segona Catalana",      "58161868"),
    "filial":    ("37205",    "Filial",       "Quarta Catalana",      "58161922"),
    "femeni":    ("54314027", "Femeni",       "Preferent Femenina",   "58162315"),
    "femeniB":   ("43977790", "Femeni B",     "Segona Divisió",       None),
    "juvenil":   ("39200",    "Juvenil",      "Segona Divisió",       None),
    "cadet":     ("54331379", "Cadet",        "Primera Divisió",      None),
    "infantil":  ("50600040", "Infantil A",   "Primera Divisió",      None),
    "infantil2": ("54314028", "Infantil B",   "Segona Divisió",       None),
    "alevi1":    ("47584913", "Alevi S12",    "Primera Divisió",      None),
    "alevi2":    ("48100832", "Alevi S12",    "Segona Divisió",       None),
    "alevi":     ("54314020", "Alevi S11",    "Preferent",            "58162088"),
    "alevi4":    ("58156640", "Alevi S11",    "Primera Divisió",      None),
    "benjami":   ("50599804", "Benjami",      "Primera Divisió",      None),
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "ca,es;q=0.9",
    "Referer": "https://www.fcf.cat/ca/clubs/3085",
}


def get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


# ---------- neteja de noms de rival ----------
_MAP = {"C.D.C.": "CDC", "U.D.C.": "UDC", "C.D.": "CD", "C.F.": "CF", "U.E.": "UE",
        "U.D.": "UD", "A.E.C.": "AEC", "A.E.": "AE", "C.E.": "CE", "A.D.": "AD",
        "E.F.B.": "EFB", "E.F.": "EF", "S.C.E.R.": "SCER", "S.C.": "SC", "F.C.": "FC",
        "F.S.": "FS", "C.P.": "CP", "U.C.F.": "UCF", "AT.": "AT", "ATL.": "Atletic",
        "Pª": "PB", "BARC.": "", "BARC": "", "C.": "", "CLUB": ""}
_LOWER = {"de", "del", "dels", "la", "les", "el", "i", "es", "d'", "l'"}
_KEEP = {"CF", "CD", "CDC", "UE", "UD", "UDC", "AE", "AEC", "CE", "AD", "EF", "EFB",
         "SC", "SCER", "FC", "AF", "PB", "FS", "CP", "AT", "UCF", "CFF", "FCF"}


def _tc(w):
    return "-".join(p[:1].upper() + p[1:].lower() for p in w.split("-"))


def clean_name(raw):
    if not raw:
        return ""
    s = re.sub(r"\s+", " ", raw).strip()
    s = re.sub(r'\s+"?[A-Za-z]"?\s*$', "", s)          # lletra d'equip ("A", B...)
    s = re.sub(r"\s*\(RET.*?\)\s*", "", s, flags=re.I).strip(" ,")
    s = re.sub(r"ASSOC(?:IACIO)?\.?\s*FUTBOL", "AF", s, flags=re.I)
    if "ALDEANA" in s.upper():
        return CLUB
    if "," in s:
        head, tail = s.rsplit(",", 1)
        s = (tail.strip() + " " + head.strip()).strip()
    out = []
    for i, w in enumerate(s.split(" ")):
        w = _MAP.get(w, _MAP.get(w.rstrip("."), w))
        if not w or re.fullmatch(r"[A-Za-z]\.", w):
            continue
        u = w.upper().replace(".", "")
        if u in _KEEP:
            out.append(u)
        elif i and w.lower() in _LOWER:
            out.append(w.lower())
        elif "'" in w and w == w.upper():
            a, b = w.split("'", 1)
            out.append(a.lower() + "'" + _tc(b))
        elif w == w.upper() or w == w.lower():
            out.append(_tc(w))
        else:
            out.append(w)
    return re.sub(r"\s+", " ", " ".join(out)).strip()


def short_venue(campo, opp):
    v = (campo or "").upper()
    for p in ("ESTADI MUNICIPAL", "ESTADI MPAL.", "CAMP DE FUTBOL MUNICIPAL",
              "CAMP DE FUTBOL MPAL.", "CAMP DE FUTBOL", "CAMP MUNICIPAL", "CAMPO DE FUTBOL",
              "ESTADI", "PISTA", "MUNICIPAL", "MPAL.", "ANNEX", "C.F.", "C.D.", "U.E.", "U.D.",
              " DE ", " D'", " D´", "Nº", "N°"):
        v = v.replace(p, " ")
    v = re.sub(r"[0-9]+", " ", v)
    v = re.sub(r"\s+", " ", v).strip(" .'´-")
    v = " ".join(_tc(w) for w in v.split(" ") if w)
    return v or _tc(clean_name(opp).split(" ")[-1])


def jint(x):
    try:
        return int(str(x).strip() or "0")
    except Exception:
        return 0


# ---------- descarrega ----------
team_matches = {}
for tid, (code, *_rest) in TEAMS.items():
    d = get_json("https://www.fcf.cat/api/clubs/3085/team/%s" % code)
    team_matches[tid] = (d.get("data") or {}).get("matches") or []
    print("  %-10s %3d partits" % (tid, len(team_matches[tid])))

# ---------- MATCHES (proper partit de cada equip) ----------
match_rows = []
for tid, (code, name, comp, grp) in TEAMS.items():
    up = sorted([m for m in team_matches[tid] if (m.get("COMIENZO1") or "")[:10] >= TODAY],
                key=lambda m: m["COMIENZO1"])
    if not up:
        continue
    m = up[0]
    home = m.get("CODCLUB_CASA") == "3085"
    opp = clean_name(m["NOMBRE_FUERA"] if home else m["NOMBRE_CASA"])
    dt = m["COMIENZO1"]
    date, time = dt[:10], dt[11:16]
    jr = jint(m.get("JORNADA"))
    label = "Amistós" if jr == 0 else "%s · Jornada %d" % (comp, jr)
    venue = "FIELD" if home else json.dumps(short_venue(m.get("CAMPO"), opp), ensure_ascii=False)
    h = "CLUB" if home else json.dumps(opp, ensure_ascii=False)
    a = json.dumps(opp, ensure_ascii=False) if home else "CLUB"
    match_rows.append(
        "  {catId:%s,comp:%s,home:%s,away:%s,date:%s,time:%s,venue:%s}" % (
            json.dumps(tid), json.dumps(label, ensure_ascii=False), h, a,
            json.dumps(date), json.dumps(time), venue))
MATCHES = "const MATCHES=[\n" + ",\n".join(match_rows) + "\n];" if match_rows else "const MATCHES=[];"

# ---------- RESULTATS jugats aquesta temporada ----------
def played_results(tid):
    out = []
    for m in team_matches[tid]:
        d10 = (m.get("COMIENZO1") or "")[:10]
        if not (SEASON_START <= d10 <= TODAY):
            continue
        if m.get("CERRADA") != "1":
            continue
        gc, gf = m.get("GOLES_CASA"), m.get("GOLES_FUERA")
        if gc is None or gf is None:
            continue
        if gc in ("0", 0) and gf in ("0", 0) and not m.get("ESTADO"):
            continue
        home = m.get("CODCLUB_CASA") == "3085"
        opp = clean_name(m["NOMBRE_FUERA"] if home else m["NOMBRE_CASA"])
        jr = jint(m.get("JORNADA"))
        out.append((m["COMIENZO1"], {
            "d": d10, "hv": "H" if home else "V", "rival": opp,
            "sc": "%s-%s" % (jint(gc), jint(gf)),
            "comp": "Amistós" if jr == 0 else "Jornada %d" % jr}))
    out.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in out]


def js_results(lst):
    return "[" + ",".join(
        "{d:%s,hv:%s,rival:%s,sc:%s,comp:%s}" % (
            json.dumps(r["d"]), json.dumps(r["hv"]), json.dumps(r["rival"], ensure_ascii=False),
            json.dumps(r["sc"]), json.dumps(r["comp"], ensure_ascii=False))
        for r in lst) + "]"


T1_RESULTS = "const T1_RESULTS=" + js_results(played_results("primer")) + ";"
tr = {tid: played_results(tid) for tid in TEAMS if tid != "primer"}
tr = {k: v for k, v in tr.items() if v}
TEAM_RESULTS = ("const TEAM_RESULTS={\n"
                + ",\n".join(" %s:%s" % (k, js_results(v)) for k, v in tr.items())
                + "\n};") if tr else "const TEAM_RESULTS={};"

# ---------- CLASSIFICACIONS (nomes si la lliga ha comencat) ----------
def classification(grp):
    d = get_json("https://www.fcf.cat/api/competition/classificacio?grupId=%s" % grp)
    rows = d.get("data") or []
    out = []
    for r in rows:
        tm = r.get("team") or {}
        nm = tm.get("name", "") or ""
        me = "ALDEANA" in nm.upper()
        out.append({
            "n": CLUB if me else clean_name(nm),
            "pj": jint(r.get("played")), "g": jint(r.get("won")), "e": jint(r.get("drawn")),
            "p": jint(r.get("lost")), "gf": jint(r.get("goalsFor")), "gc": jint(r.get("goalsAgainst")),
            "pts": round(float(str(r.get("points") or "0"))), "me": me})
    return out


def js_table_rows(rows):
    return ",".join(
        "{n:%s,pj:%d,g:%d,e:%d,p:%d,gf:%d,gc:%d,pts:%d%s}" % (
            json.dumps(r["n"], ensure_ascii=False), r["pj"], r["g"], r["e"], r["p"],
            r["gf"], r["gc"], r["pts"], ",me:1" if r.get("me") else "")
        for r in rows)


live_tables = {}   # tid -> rows  (nomes grups amb pj>0)
for tid, (code, name, comp, grp) in TEAMS.items():
    if not grp:
        continue
    try:
        rows = classification(grp)
    except Exception as e:
        print("  classificacio %s: %s" % (tid, e))
        continue
    if rows and any(r["pj"] > 0 for r in rows):
        live_tables[tid] = rows
        print("  taula viva: %s (%d equips)" % (tid, len(rows)))


# ---------- aplicar sobre index.html ----------
src = open(HTML, encoding="utf-8").read()
orig = src
mister_before = re.search(r'id="mister-note">(.*?)</script>', src, re.S).group(1)


def find_const(text, name):
    m = re.search(r"const %s\s*=\s*" % re.escape(name), text)
    if not m:
        raise SystemExit("NO TROBAT: const %s" % name)
    i = m.end()
    while text[i] in " \t\n":
        i += 1
    if text[i] in "[{":
        op, cl = text[i], {"[": "]", "{": "}"}[text[i]]
        depth, k, instr, esc = 0, i, None, False
        while k < len(text):
            c = text[k]
            if instr:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == instr:
                    instr = None
            else:
                if c in "\"'":
                    instr = c
                elif c == op:
                    depth += 1
                elif c == cl:
                    depth -= 1
                    if depth == 0:
                        k += 1
                        break
            k += 1
        end = k
    else:
        end = text.index(";", i)
    while end < len(text) and text[end] != ";":
        end += 1
    return m.start(), end + 1


def replace_const(text, name, new_code):
    a, b = find_const(text, name)
    return text[:a] + new_code + text[b:]


src = replace_const(src, "MATCHES", MATCHES)
src = replace_const(src, "T1_RESULTS", T1_RESULTS)
src = replace_const(src, "TEAM_RESULTS", TEAM_RESULTS)
src = replace_const(src, "FIXTURES_UPDATED", "const FIXTURES_UPDATED=%s;" % json.dumps(TODAY))

if "primer" in live_tables:
    src = replace_const(src, "T1_TABLE", "const T1_TABLE=[\n  " + js_table_rows(live_tables["primer"]).replace("},{", "},\n  {") + "\n];")
    src = replace_const(src, "T1_TABLE_UPDATED", "const T1_TABLE_UPDATED=%s;" % json.dumps(TODAY))

others = {k: v for k, v in live_tables.items() if k != "primer"}
if others:
    a, b = find_const(src, "TEAM_TABLE")
    cur = src[a:b]
    inner = cur[cur.index("{") + 1:cur.rindex("}")]
    parts = {}
    for km in re.finditer(r"(\w+):\[", inner):
        key = km.group(1)
        depth, k = 0, km.end() - 1
        while k < len(inner):
            if inner[k] == "[":
                depth += 1
            elif inner[k] == "]":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        parts[key] = inner[km.end() - 1:k + 1]
    for key, rows in others.items():
        parts[key] = "[" + js_table_rows(rows) + "]"
    new_tt = "const TEAM_TABLE={\n" + ",\n".join(" %s:%s" % (k, v) for k, v in parts.items()) + "\n};"
    src = src[:a] + new_tt + src[b:]

# ---------- comprovacions ----------
def fail(msg):
    print("\n[ABORTAT] " + msg)
    sys.exit(1)

if src == orig:
    print("\nSense canvis.")
    sys.exit(0)

for marker in ("<title>U.E. Aldeana", 'id="mister-note"', "function initXat", "function teamPageView",
               "firebase.initializeApp", "AUTO-DATA (FCF)"):
    if marker not in src:
        fail("falta el marcador: " + marker)

if re.search(r'id="mister-note">(.*?)</script>', src, re.S).group(1) != mister_before:
    fail("la nota del mister ha canviat")

if not (0.85 < len(src) / len(orig) < 1.15):
    fail("mida sospitosa: %d -> %d bytes" % (len(orig), len(src)))

import shutil
if shutil.which("node"):
    main = src.index("<script>\nvar CANON_HTML")
    js = src[main + len("<script>"):src.index("</script>", main)]
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js)
        tmpjs = f.name
    try:
        r = subprocess.run(["node", "--check", tmpjs], capture_output=True, text=True)
    finally:
        os.unlink(tmpjs)
    if r.returncode != 0:
        fail("node --check ha fallat:\n" + r.stderr[-1500:])
    print("  node --check: OK")
elif os.environ.get("CI"):
    fail("node no disponible al runner de CI")
else:
    print("  (node no instal.lat: salto la comprovacio de sintaxi en local)")

with io.open(HTML, "w", encoding="utf-8", newline="\n") as f:
    f.write(src)

print("\nOK  ·  %+d bytes  ·  %d partits, %d equips amb resultats, %d taules vives"
      % (len(src) - len(orig), len(match_rows), len(tr), len(live_tables)))
