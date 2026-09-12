#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Envia una notificacio push quan un soci publica una noticia des de l'app
(node news_live/<id> a la Realtime Database, escrit des de la pagina
"Publica una noticia" de Noticies).

S'executa cada 15 min des de .github/workflows/notify-news-live.yml.
Compara les noticies actuals amb la marca previa_meta... la marca
news_live_meta/last_key (la darrera push-id ja avisada; les push-id de
Firebase son ordenables cronologicament) i avisa nomes de les noves.

Necessita el secret FIREBASE_SA (clau de compte de servei de Firebase, JSON).
"""
import json, os, re, sys, time

DB_URL = "https://uealdeana-929a8-default-rtdb.europe-west1.firebasedatabase.app"
SITE = os.environ.get("SITE_URL", "https://uea-d1zy.vercel.app").rstrip("/")
MAX_BURST = 3
MAX_AGE_MS = 6 * 60 * 60 * 1000


def snippet(text, n=140):
    t = re.sub(r"\s+", " ", (text or "")).strip()
    return t if len(t) <= n else t[:n - 1].rstrip() + "…"


sa = os.environ.get("FIREBASE_SA")
if not sa:
    print("Falta el secret FIREBASE_SA."); sys.exit(1)

import firebase_admin
from firebase_admin import credentials, messaging, db

firebase_admin.initialize_app(credentials.Certificate(json.loads(sa)), {"databaseURL": DB_URL})

items = db.reference("news_live").order_by_key().limit_to_last(10).get() or {}
if not items:
    print("Encara no hi ha cap noticia publicada des de l'app."); sys.exit(0)

last_key = db.reference("news_live_meta/last_key").get()
keys_sorted = sorted(items.keys())

if last_key is None:
    # primer cop que corre: no bombardegem amb tot l'historial, nomes marquem.
    db.reference("news_live_meta/last_key").set(keys_sorted[-1])
    print("Primer cop: marco la darrera noticia sense avisar."); sys.exit(0)

new_keys = [k for k in keys_sorted if k > last_key]
if not new_keys:
    print("Cap noticia nova."); sys.exit(0)
if len(new_keys) > MAX_BURST:
    new_keys = new_keys[-MAX_BURST:]

now_ms = int(time.time() * 1000)
tokens = sorted({v for v in (db.reference("push_tokens").get() or {}).values() if isinstance(v, str)})
print("%d noticia(es) nova(es), %d dispositiu(s) subscrit(s)." % (len(new_keys), len(tokens)))

try:
    from firebase_admin.messaging import UnregisteredError, SenderIdMismatchError
    _STALE = (UnregisteredError, SenderIdMismatchError)
except Exception:
    _STALE = ()

stale = set()
for k in new_keys:
    it = items[k] or {}
    at = it.get("at") or 0
    if (now_ms - int(at)) > MAX_AGE_MS:
        continue  # noticia vella (p.ex. recuperada d'un backup); no avisem
    title = it.get("title") or "Nova notícia"
    body = "%s: %s" % (title, snippet(it.get("body")))
    if tokens:
        for i in range(0, len(tokens), 500):
            batch = tokens[i:i + 500]
            resp = messaging.send_each_for_multicast(messaging.MulticastMessage(
                tokens=batch,
                notification=messaging.Notification(title="U.E. Aldeana", body=body),
                webpush=messaging.WebpushConfig(
                    notification=messaging.WebpushNotification(icon=SITE + "/icons/icon-192.png"),
                    fcm_options=messaging.WebpushFCMOptions(link=SITE + "/#noticies"),
                ),
            ))
            for j, r in enumerate(resp.responses):
                if not r.success and (isinstance(r.exception, _STALE) or
                                      "not-registered" in str(getattr(r.exception, "code", "")).lower()):
                    stale.add(batch[j])
        print("  · %s" % body)

db.reference("news_live_meta/last_key").set(keys_sorted[-1])
for t in stale:
    db.reference("push_tokens/" + re.sub(r"[^A-Za-z0-9_-]", "_", t)).delete()
if stale:
    print("Netejats %d tokens caducats." % len(stale))
