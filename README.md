# U.E. Aldeana · App

App web de la **Unió Esportiva Aldeana** (l'Aldea, Baix Ebre). Equips, calendaris,
classificacions, cròniques i xat de cada equip. És una sola pàgina, sense servidor
ni compilació: només fitxers estàtics.

---

## Estructura

```
index.html              · tota l'app (HTML + CSS + JS + imatges, en un sol fitxer)
manifest.webmanifest    · dades per instal·lar-la com a app al mòbil
sw.js                   · service worker (funciona sense connexió + càrrega ràpida)
icons/                  · icones de l'app (escut del club sobre fons blau marí)
.nojekyll               · perquè GitHub Pages serveixi els fitxers tal qual
```

---

## Publicar-la a GitHub Pages

1. Crea un repositori nou a GitHub (per exemple `uealdeana-app`) i puja-hi
   tot el contingut d'aquesta carpeta (que `index.html` quedi a l'arrel).
2. Al repositori: **Settings → Pages**.
3. A *Build and deployment* → *Source*: **Deploy from a branch**.
4. Branch: **main**, carpeta **/ (root)** → **Save**.
5. Al cap d'un minut tindràs l'app a
   `https://EL-TEU-USUARI.github.io/uealdeana-app/`.

> Amb domini propi: afegeix un fitxer `CNAME` amb el domini i configura'l a *Settings → Pages*.

### Alternativa ràpida (sense GitHub)

Arrossega aquesta carpeta a **https://app.netlify.com/drop** i tindràs una URL
al moment.

---

## El xat dels equips (Firebase)

El xat fa servir **Firebase Realtime Database**. La configuració ja està dins
`index.html` (busca `firebase.initializeApp`). L'*apiKey* de Firebase per a web
**no és secreta** — la seguretat es fa amb les regles de la base de dades.

Perquè el xat funcioni, a la consola de Firebase → **Realtime Database → Regles**,
enganxa:

```json
{
  "rules": {
    "xat": {
      "$room": {
        ".read": true,
        ".write": true,
        "$msg": {
          ".validate": "newData.hasChildren(['n','x','t']) && newData.child('n').isString() && newData.child('n').val().length <= 24 && newData.child('x').isString() && newData.child('x').val().length >= 1 && newData.child('x').val().length <= 500"
        }
      }
    }
  }
}
```

Moderació: pots esborrar qualsevol missatge des de **Realtime Database → Dades**.

Si algun dia vols fer servir un altre projecte de Firebase, canvia només el bloc
`firebase.initializeApp({ ... })` de `index.html`.

---

## Actualitzar l'app

1. Edita `index.html` (o torna a exportar-lo des de l'eina de sempre).
2. **Important:** obre `sw.js` i puja el número de versió:
   `const CACHE = 'uea-v1'` → `'uea-v2'`, etc.
   Sense això, els mòbils que ja tenen l'app instal·lada seguiran veient la
   versió antiga (el service worker la té a la memòria cau).
3. Puja els canvis a GitHub. GitHub Pages es refresca sol en 1–2 minuts.

---

## Notes

- La "Nota del Míster / ⚽ LA PRÈVIA DEL PARTIT" es guarda al dispositiu quan
  l'app està allotjada fora de claude.ai (la publicació compartida només
  funciona a l'artifact original).
- Els calendaris i classificacions estan integrats a mà a partir de les dades
  de la Federació Catalana de Futbol; s'actualitzen editant `index.html`.
- Dades i imatges: Federació Catalana de Futbol i uealdeana.com.
