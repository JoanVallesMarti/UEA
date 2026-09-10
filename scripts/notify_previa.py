#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Envia una notificacio push quan es publica una NOVA previa del partit.

La previa NO es a cap commit: l'escriu l'app directament a la Realtime Database
(node previa/primer). Aquest script s'executa cada 15 min des de
.github/workflows/notify-previa.yml, compara la previa actual amb l'ultima
que ja s'ha avisat (marca previa_meta/last_notified_at) i, si ha canviat i
encara es recent, envia el push a tots els dispositius subscrits (push_tokens).

Necessita el secret FIREBASE_SA (clau de compte de servei de Firebase, JSON).
"""
import json, os, re, sys, time

DB_URL = "https://uealdeana-929a8-default-rtdb.europe-west1.firebasedatabase.app"
SITE = os.environ.get("SITE_URL", "https://uea-d1zy.vercel.app").rstrip("/")
MAX_AGE_MS = 6 * 60 * 60 * 1000   # nomes avisem si la previa te menys de 6 h


def snippet(text, n=140):
    t = re.sub(r"\s+", " ", (text or "")).strip()
    return t if len(t) <= n else t[:n - 1].rstrip() + "…"


sa = os.environ.get("FIREBASE_SA")
if not sa:
    print("Falta el secret FIREBASE_SA."); sys.exit(1)

import firebase_admin
from firebase_admin import credentials, messaging, db

firebase_admin.initialize_app(credentials.Certificate(json.loads(sa)), {"databaseURL": DB_URL})

previa = db.reference("previa/primer").get() or {}
text = previa.get("t")
at = previa.get("at")

if not text or not at:
    print("Encara no hi ha cap previa publicada."); sys.exit(0)

last = db.reference("previa_meta/last_notified_at").get()

if last == at:
    print("La previa no ha canviat des de l'ultim avis."); sys.exit(0)

now_ms = int(time.time() * 1000)
recent = (now_ms - int(at)) < MAX_AGE_MS

# Sigui com sigui, deixem la marca al dia perque no la tornem a considerar.
db.reference("previa_meta/last_notified_at").set(at)

if not recent:
    print("Previa canviada pero antiga (%d min); no avisem, nomes marquem." % ((now_ms - int(at)) // 60000))
    sys.exit(0)

tokens = sorted({v for v in (db.reference("push_tokens").get() or {}).values() if isinstance(v, str)})
print("Previa nova. %d dispositiu(s) subscrit(s)." % len(tokens))
if not tokens:
    sys.exit(0)

try:
    from firebase_admin.messaging import UnregisteredError, SenderIdMismatchError
    _STALE = (UnregisteredError, SenderIdMismatchError)
except Exception:
    _STALE = ()

body = "Nova prèvia del partit: " + snippet(text)
stale = set()
sent = 0
for k in range(0, len(tokens), 500):
    batch = tokens[k:k + 500]
    resp = messaging.send_each_for_multicast(messaging.MulticastMessage(
        tokens=batch,
        notification=messaging.Notification(title="U.E. Aldeana", body=body),
        webpush=messaging.WebpushConfig(
            notification=messaging.WebpushNotification(icon=SITE + "/icons/icon-192.png"),
            fcm_options=messaging.WebpushFCMOptions(link=SITE + "/"),
        ),
    ))
    sent += resp.success_count
    for i, r in enumerate(resp.responses):
        if not r.success and (isinstance(r.exception, _STALE) or
                              "not-registered" in str(getattr(r.exception, "code", "")).lower()):
            stale.add(batch[i])

print("Enviades: %d" % sent)
for t in stale:
    db.reference("push_tokens/" + re.sub(r"[^A-Za-z0-9_-]", "_", t)).delete()
if stale:
    print("Netejats %d tokens caducats." % len(stale))
