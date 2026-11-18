# Prompt EnginEEr

Wandelt frei und unbeholfen formulierte Prompts per LLM in optimierte,
kopierbare Prompts um. Desktop (Windows 11, Linux) und Android, gleiche
Python-Logik und Oberfläche. Ein Projekt von [Eisberg Tech](https://eisberg-tech.de).

Version: siehe [CHANGELOG.md](CHANGELOG.md) (aktuell 1.4.1).
Kurzbeschreibung und Links: [DESCRIPTION.md](DESCRIPTION.md).

## Inhalt

- [Funktion](#funktion)
- [Voraussetzungen](#voraussetzungen)
- [Installation und Start](#installation-und-start)
- [Desktop-Builds (PyInstaller, Nuitka)](#desktop-builds-pyinstaller-nuitka)
- [Android](#android)
- [Bedienung](#bedienung)
- [Skripte](#skripte)
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

Einstellungen liegen in `.env` neben der App (Schlüssel `API_TYPE`,
`BASE_URL`, `API_KEY`, `MODEL`, `THEME`, `LAYOUT`; Vorlage `.env.example`).
Normalweg: in der App unter Einstellungen pflegen, die App schreibt `.env`
selbst. Historie: `history.db` (SQLite), Fehlerlog: `app.log`.

## Voraussetzungen

| Plattform | Voraussetzung |
|---|---|
| Linux (Debian/Ubuntu) | Python 3.11+, GTK 3 + WebKit2GTK 4.1 über `python3-gi` (`sudo apt install python3-gi gir1.2-webkit2-4.1`); `.venv` mit `--system-site-packages` |
| Linux, Nuitka-Build | zusätzlich `sudo apt install gcc patchelf python3-dev` |
| Linux ohne Display (Build-Selftest) | `sudo apt install xvfb` |
| Windows 11 | Python 3.11+ (`py`-Launcher), WebView2 Runtime (vorinstalliert), Git Bash für die `.sh`-Skripte |
| Windows, Nuitka-Build | zusätzlich Visual Studio Build Tools (MSVC) |
| Android-Build | JDK 17/21, Android SDK 36, Details: [Android](#android) |

Laufzeit-Abhängigkeiten (`requirements.txt`): pywebview, httpx,
python-dotenv. `requirements-dev.txt` ergänzt pytest, PyInstaller, Nuitka
(gepinnte Versionen).

## Installation und Start

Linux:

```bash
./000_install.sh                              # .venv + requirements.txt
.venv/bin/python -m pip install -r requirements-dev.txt   # optional: Tests, Builds
./001_start.sh                                # App im Hintergrund (PID in .run/app.pid)
./002_stop.sh                                 # App beenden
```

Windows (Git Bash oder PowerShell, einmalig):

```bash
py -3.11 -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python main.py
```

Direkt (Linux-Pfade, unter Windows `.venv/Scripts/python`):

```bash
.venv/bin/python main.py              # App starten
.venv/bin/python main.py --selftest   # Prüflauf, Exit 0 = grün
.venv/bin/python -m pytest -q         # Tests, ohne Netz
```

`--selftest`: verstecktes Fenster, prüft Seitenaufbau, js_api
(`get_settings`), beschreibbaren App-Ordner, SQLite. Legt weder `.env` noch
`history.db` noch `app.log` an.

## Desktop-Builds (PyInstaller, Nuitka)

Beide Builds laufen über `build.py` und funktionieren unter Linux und Windows
(Build immer auf dem Zielsystem, kein Cross-Compile). Nach dem Build startet
`build.py` die erzeugte App mit `--selftest` und prüft, dass keine
Laufzeit-Dateien im Ausgabe-Ordner liegen. Exit 0 nur wenn alles grün ist.

```bash
./013_build_pyinstaller.sh            # PyInstaller, Single-Folder (--onedir)
./014_build_nuitka.sh                 # Nuitka, Standalone
```

Die Skripte

- lesen die Version aus dem ersten `## [X.Y.Z]`-Eintrag in `CHANGELOG.md`
  (ohne Eintrag: Menü bzw. `--fallback-version`, Ausgabe-Ordner bekommt dann
  das Suffix `_no-changelog`),
- wählen das Python der `.venv` (Linux `.venv/bin/python`, Git Bash unter
  Windows `.venv/Scripts/python.exe`),
- installieren fehlendes PyInstaller/Nuitka in der Version aus
  `requirements-dev.txt`,
- prüfen unter Linux `gcc` und `patchelf` (Nuitka) und nutzen `xvfb-run`,
  wenn kein Display vorhanden ist,
- reichen die Paket- und Daten-Flags aus `BUILD_ARGS` (eigene Pakete
  `controllers`, `models`, `services`, Vorlage `.env.example`) per
  `--tool-arg` an `build.py` durch.

Optionen: `--no-pause` (kein "Enter zum Schließen"), `--fallback-version
0.0.0|X.Y.Z|abort`. Exit-Codes: 0 OK, 1 Fehler, 2 Abbruch.

Direkt:

```bash
.venv/bin/python build.py pyinstaller | nuitka | all [--version X.Y.Z] [--tool-arg=FLAG ...]
```

`--version` setzt unter Windows die Versionsressource der exe (PyInstaller
`--version-file`, Nuitka `--product-version`/`--file-version`); unter Linux
ohne Wirkung. Logs: `build/pyinstaller.log`, `build/nuitka.log`.

Ausgabe (Single-Folder, portabel kopierbar):

| Build | Linux | Windows |
|---|---|---|
| PyInstaller | `dist/pyinstaller/PromptEnginEEr/PromptEnginEEr` | `dist\pyinstaller\PromptEnginEEr\PromptEnginEEr.exe` |
| Nuitka | `dist/nuitka/PromptEnginEEr/PromptEnginEEr` | `dist\nuitka\PromptEnginEEr\PromptEnginEEr.exe` |

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
| NV2 | Android SDK Platform 36, Build-Tools, Platform-Tools; `ANDROID_HOME` (Default `~/Android/Sdk`) | `adb version` |
| NV3 | Gradle-Wrapper in `android/` | `android/gradlew --version` |
| NV4 | Netzzugang beim ersten Gradle-Lauf | - |
| NV5 | Optional: Emulator-AVD (x86_64) | `emulator -list-avds` |

```bash
./003_build_apk.sh                                  # Debug-APK, Version aus CHANGELOG.md
android/gradlew -p android connectedDebugAndroidTest   # Gerätetests (SelfTest.kt)
```

Ausgabe: `android/app/build/outputs/apk/`, Kopie nach
`z_APKs/PromptEnginEEr_<Version>_<debug|release>.apk`. Release ohne
`android/keystore.properties` wird mit Debug-Signatur gebaut, nicht zur
Weitergabe. Eigener Keystore: [INFRA.md](INFRA.md).

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

## Skripte

Bash, lokal, gitignored (`*.sh`). Alle Skripte: `--no-pause`, Exit 0 OK,
1 Fehler, 2 Abbruch.

| Skript | Zweck |
|---|---|
| `000_install.sh` | `.venv` anlegen, `requirements.txt` installieren |
| `001_start.sh` | App im Hintergrund starten, Logs `.run/app.out.log`, `.run/app.err.log` |
| `002_stop.sh` | App beenden (PID-File mit Identitätsprüfung) |
| `003_build_apk.sh` | Android-APK (Gradle), Version aus `CHANGELOG.md`, Kopie nach `z_APKs/` |
| `006_github_push.sh` | Commit + Push nach GitHub (`--message`, `--branch`, `--dry-run`) |
| `007_github_force_push.sh` | Force-Push nach GitHub, Remote-Commits werden überschrieben |
| `008_github_wipe_history.sh` | Git-Historie auf GitHub durch einen Commit ersetzen |
| `013_build_pyinstaller.sh` | Desktop-Build PyInstaller + Selftest (Linux, Windows/Git Bash) |
| `014_build_nuitka.sh` | Desktop-Build Nuitka + Selftest (Linux, Windows/Git Bash) |

Nummern 004-005 (Docker) und 009-012 (Git-Helfer, Codeberg) sind reserviert,
daher die Desktop-Builds auf 013/014.

## Struktur

```
main.py                 Bootstrap, Fenster, --selftest
build.py                PyInstaller-/Nuitka-Build + Selftest (Linux, Windows)
android_entry.py        Android-Einstieg (Chaquopy), Dispatcher auf controllers/api.py
controllers/api.py      pywebview js_api (Brücke UI <-> Python)
services/paths.py       App- und Ressourcen-Pfade
services/settings.py    .env laden/speichern/validieren
services/providers.py   OpenAI-/Anthropic-Adapter (Modelle, Chat)
services/optimizer.py   System-Prompt, JSON-Protokoll, Schrittlogik
models/history.py       SQLite-Historie
static/                 index.html, app.css, app.js (View), fonts/, assets/
design/                 Layout-Mockups Werkbank / Fokus (Referenz, nicht ausgeliefert)
android/                Android-Projekt (Gradle, Kotlin-Hülle, WebView)
tests/                  pytest, ohne Netz (httpx.MockTransport)
0??_*.sh                Install, Start, Stop, Builds, Git (lokal)
```

Schichten-Zuordnung: [MVC.md](MVC.md). Begründung: [ERKLAERUNG.md](ERKLAERUNG.md).
Pfade, Netz, Builds: [INFRA.md](INFRA.md).

## Links

- Eisberg Tech: <https://eisberg-tech.de>
- Quellcode: <https://github.com/Nope-im-not-pro/PromptEngineer>
- Releases: <https://github.com/Nope-im-not-pro/PromptEngineer/releases>
- Fehler melden: <https://github.com/Nope-im-not-pro/PromptEngineer/issues>

## Kaskade

Root-Ebene, keine Eltern-Doku. Module/Features tragen sich hier spartanisch ein.
