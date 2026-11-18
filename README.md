# Prompt EnginEEr

Wandelt frei und unbeholfen formulierte Prompts per LLM in optimierte,
kopierbare Prompts um. Desktop (Windows 11, Linux) und Android, gleiche
Python-Logik und Oberfläche. Ein Projekt von [Eisberg Tech](https://eisberg-tech.de).

Version: siehe [CHANGELOG.md](CHANGELOG.md).
Kurzbeschreibung und Links: [DESCRIPTION.md](DESCRIPTION.md).

## Inhalt

- [Funktion](#funktion)
- [Voraussetzungen](#voraussetzungen)
- [Installation und Start](#installation-und-start)
- [Desktop-Builds (PyInstaller, Nuitka)](#desktop-builds-pyinstaller-nuitka)
- [Android](#android)
- [Bedienung](#bedienung)
- [Struktur](#struktur)
- [Links](#links)

## Funktion

1. Roh-Prompt eingeben.
2. Ist die Absicht unklar, stellt das LLM genau eine Rückfrage (Aufgabenart
   oder Zielergebnis) mit 2-5 Antwortvorgaben. Klarer Prompt -> direkt
   Schritt 4.
3. Vorgabe per Klick wählen oder Prompt neu formulieren (dann zurück zu 2).
4. Optimierter Prompt, kopierbar.

Weiter: Historie (Liste, Detail, Kopieren, Löschen), Einstellungen (API-Typ,
Basis-URL, API-Key, Modell, Darstellung, Layout). Anbieter frei wählbar:
OpenAI-kompatible oder Anthropic-kompatible API, die Modellliste wird
automatisch abgefragt.

| API_TYPE | BASE_URL |
|---|---|
| openai | `https://api.openai.com/v1` |
| openai (lokal, z. B. Ollama; API-Key leer lassen) | `http://localhost:11434/v1` |
| anthropic | `https://api.anthropic.com` |

Einstellungen speichert die App in einer Einstellungsdatei neben der
Programmdatei (Schlüssel `API_TYPE`, `BASE_URL`, `API_KEY`, `MODEL`, `THEME`,
`LAYOUT`; Vorlage [.env.example](.env.example)). Normalweg: in der App unter
Einstellungen pflegen, die App legt die Datei selbst an. Historie und
Fehlerlog liegen ebenfalls lokal neben der App (SQLite bzw. Textdatei).

## Voraussetzungen

| Plattform | Voraussetzung |
|---|---|
| Linux (Debian/Ubuntu) | Python 3.11+, GTK 3 + WebKit2GTK 4.1 über `python3-gi` (`sudo apt install python3-venv python3-gi gir1.2-webkit2-4.1`) |
| Linux, Nuitka-Build | zusätzlich `sudo apt install gcc patchelf python3-dev` |
| Linux ohne Display (Build-Selftest) | `sudo apt install xvfb`, Build über `xvfb-run -a` |
| Windows 11 | Python 3.11+ (`py`-Launcher), WebView2 Runtime (vorinstalliert) |
| Windows, Nuitka-Build | zusätzlich Visual Studio Build Tools (MSVC) |
| Android-Build | JDK 17/21, Android SDK 36, Details: [Android](#android) |

Laufzeit-Abhängigkeiten ([requirements.txt](requirements.txt)): pywebview,
httpx, python-dotenv. [requirements-dev.txt](requirements-dev.txt) ergänzt
pytest, PyInstaller, Nuitka (gepinnte Versionen).

## Installation und Start

Virtuelle Umgebung anlegen und aktivieren (Name frei wählbar, hier `<venv>`).
Unter Linux mit `--system-site-packages`, damit `python3-gi` der System-Python
sichtbar ist.

Linux:

```bash
python3 -m venv --system-site-packages <venv>
source <venv>/bin/activate
python -m pip install -r requirements-dev.txt
```

Windows (PowerShell):

```powershell
py -3.11 -m venv <venv>
<venv>\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Danach (beide Plattformen, Umgebung aktiv):

```bash
python main.py              # App starten
python main.py --selftest   # Prüflauf, Exit 0 = grün
python -m pytest -q         # Tests, ohne Netz
```

`--selftest`: verstecktes Fenster, prüft Seitenaufbau, js_api
(`get_settings`), beschreibbaren App-Ordner, SQLite. Legt weder
Einstellungsdatei noch Historie noch Log an.

## Desktop-Builds (PyInstaller, Nuitka)

Beide Builds laufen über [build.py](build.py), unter Linux und Windows (Build
immer auf dem Zielsystem, kein Cross-Compile). Nach dem Build startet
`build.py` die erzeugte App mit `--selftest` und prüft, dass im
Ausgabe-Ordner keine Laufzeit-Dateien entstanden sind. Exit 0 nur wenn alles
grün ist.

```bash
python build.py pyinstaller --version 1.4.1 \
  --tool-arg=--collect-submodules=controllers \
  --tool-arg=--collect-submodules=models \
  --tool-arg=--collect-submodules=services

python build.py nuitka --version 1.4.1 \
  --tool-arg=--include-package=controllers \
  --tool-arg=--include-package=models \
  --tool-arg=--include-package=services

python build.py all          # beide nacheinander
```

| Option | Wirkung |
|---|---|
| `pyinstaller` \| `nuitka` \| `all` | Build-Werkzeug; PyInstaller als Single-Folder (`--onedir`), Nuitka `--standalone` |
| `--version X.Y.Z` | Windows: Versionsressource der exe (PyInstaller `--version-file`, Nuitka `--product-version`/`--file-version` = `X.Y.Z.0`); Linux ohne Wirkung |
| `--tool-arg=FLAG` | zusätzliches Flag für PyInstaller bzw. Nuitka, mehrfach angebbar |

Unter Windows mit PowerShell die Zeilenfortsetzung `\` durch `` ` `` ersetzen
oder alles in eine Zeile schreiben. Nuitka unter Windows nutzt MSVC; verlangt
Nuitka einen Werkzeug-Download, bricht `build.py` mit `BLOCKED` ab.

`build.py` gibt am Ende Pfad und Größe der Programmdatei sowie das
Selftest-Ergebnis aus (`RESULT: OK`). Programmdatei: `PromptEnginEEr.exe`
unter Windows, `PromptEnginEEr` unter Linux, jeweils im Ordner
`PromptEnginEEr`.

Weitergabe: kompletten Ordner `PromptEnginEEr` kopieren, nicht nur die
Programmdatei. Der Ordner muss beschreibbar sein (nicht `C:\Program Files`).
Linux-Zielsystem braucht GTK 3 und WebKit2GTK 4.1.

## Android

Gleiche Python-Logik und Oberfläche, verpackt mit Chaquopy (Python 3.11) in
einer WebView-App. Android 8.0 (API 26) bis 16 (API 36), ABIs arm64-v8a
(Geräte) und x86_64 (Emulator).

| Nr | Voraussetzung Build-Host | Prüfung |
|---|---|---|
| NV1 | JDK 17 oder 21, `JAVA_HOME` gesetzt | `java -version` |
| NV2 | Android SDK Platform 36, Build-Tools, Platform-Tools; `ANDROID_HOME` gesetzt | `adb version` |
| NV3 | Gradle-Wrapper in `android/` | `android/gradlew --version` |
| NV4 | Netzzugang beim ersten Gradle-Lauf | - |
| NV5 | Optional: Emulator-AVD (x86_64) | `emulator -list-avds` |

```bash
android/gradlew -p android :app:assembleDebug                 # Debug-APK
android/gradlew -p android :app:assembleRelease               # Release-APK
android/gradlew -p android connectedDebugAndroidTest          # Gerätetests (SelfTest.kt)
```

Unter Windows `android\gradlew.bat` statt `android/gradlew`. Version
(`versionName`, `versionCode`) steht in `android/app/build.gradle.kts`. Die APK liegt
danach im Gradle-Ausgabeordner des Moduls `app` (Unterordner
`outputs/apk/<variante>`). Ein Release-Build ohne eigene Signatur-Konfiguration
wird mit Debug-Signatur gebaut und ist nicht zur Weitergabe gedacht.

Installation (Sideload): APK aufs Gerät kopieren, "Installation aus
unbekannten Quellen" erlauben, APK öffnen; oder `adb install -r <apk>`.
Einstellungen, Historie und Log liegen im privaten App-Datenordner (nicht im
Android-Backup), Deinstallation löscht sie.

Lokales LLM (Ollama):

- Emulator: `http://10.0.2.2:11434/v1`.
- Gerät im WLAN: `http://<PC-LAN-IP>:11434/v1`, Ollama mit
  `OLLAMA_HOST=0.0.0.0` starten, Port 11434 freigeben.

Sicherheitshinweis: Die App erlaubt unverschlüsseltes HTTP an jede Adresse
(nötig für Ollama im LAN). API-Key und Prompts gehen bei `http://` im
Klartext durchs Netz. Für Cloud-Anbieter nur `https://` verwenden.

## Bedienung

Drei Tabs: Optimieren, Historie, Einstellungen.

- Erststart: Tab Einstellungen. Anbieter-Typ wählen, Basis-URL und API-Key
  eintragen, "Modelle laden", Modell wählen (oder eintragen), "Speichern".
- Optimieren, Schrittleiste "1 Eingabe -> 2 Rückfrage -> 3 Ergebnis":
  Prompt eingeben, "Optimieren"; bei Rückfrage Antwort-Button anklicken oder
  neu formulieren; Ergebnis "Kopieren", "Neuer Prompt" startet neu.
- Historie: neueste zuerst; Eintrag -> Roh-Prompt, Verlauf, Ergebnis;
  "Kopieren", "Löschen".
- Einstellungen: gespeicherter Key nur maskiert (letzte 4 Zeichen). Feld leer
  = Key bleibt, solange Anbieter-Typ und Host gleich sind (Key geht nie an
  einen neuen Host); "Key entfernen" löscht ihn.
- Darstellung: System, Hell, Dunkel (`THEME`). Layout: "Werkbank" oder
  "Fokus" (`LAYOUT`), wirkt sofort. Standard: Desktop `werkbank`, Android
  `fokus`.
  - Werkbank: Desktop mit Seitenleiste und zweispaltigem Arbeitsbereich;
    Android mit Bottom-Navigation.
  - Fokus: Desktop mit Kopfzeile und einer Wizard-Karte pro Schritt; Android
    mit App-Leiste und fester Hauptaktion unten.
- Über: Logo, App-Version, Link zum Quellcode (öffnet den System-Browser,
  andere URLs lehnt die App ab).
- Fehler (falscher Key, URL, Limit, Timeout) erscheinen als Klartext-Zeile im
  jeweiligen Tab.

Bekannte Einschränkungen Android (Dark-Mode):

- WebView ohne `prefers-color-scheme` (z. B. Chrome 69, API 26): Modus System
  zeigt Seite hell, Systemleisten folgen dem Gerät. Abhilfe: WebView
  aktualisieren oder Modus Dunkel.
- API 26-30: Modus Dunkel auf hellem Gerät zeigt beim Kaltstart kurz einen
  hellen Startbildschirm.
- API 31+: Startbildschirm-Modus gilt ab dem nächsten Kaltstart.

## Struktur

```
main.py                 Bootstrap, Fenster, --selftest
build.py                PyInstaller-/Nuitka-Build + Selftest (Linux, Windows)
android_entry.py        Android-Einstieg (Chaquopy), Dispatcher auf controllers/api.py
controllers/api.py      pywebview js_api (Brücke UI <-> Python)
services/paths.py       App- und Ressourcen-Pfade
services/settings.py    Einstellungen laden/speichern/validieren
services/providers.py   OpenAI-/Anthropic-Adapter (Modelle, Chat)
services/optimizer.py   System-Prompt, JSON-Protokoll, Schrittlogik
models/history.py       SQLite-Historie
static/                 index.html, app.css, app.js (View), fonts/, assets/
design/                 Layout-Mockups Werkbank / Fokus (Referenz, nicht ausgeliefert)
android/                Android-Projekt (Gradle, Kotlin-Hülle, WebView)
tests/                  pytest, ohne Netz (httpx.MockTransport)
```

Schichten: `models/` Persistenz, `services/` Geschäftslogik ohne UI,
`controllers/` Brücke zur Oberfläche, `static/` View.

## Links

- Eisberg Tech: <https://eisberg-tech.de>
- Quellcode: <https://github.com/Nope-im-not-pro/PromptEngineer>
- Releases: <https://github.com/Nope-im-not-pro/PromptEngineer/releases>
- Fehler melden: <https://github.com/Nope-im-not-pro/PromptEngineer/issues>

## Kaskade

Root-Ebene, keine Eltern-Doku. Module/Features tragen sich hier spartanisch ein.
