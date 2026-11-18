# Changelog - Prompt_EnginEEr_v2

Format: SemVer + ISO-Datum. Sektionen: Hinzugefuegt / Geaendert / Behoben / Entfernt / Verifiziert.

## [1.4.1] - 2026-11-18
### Hinzugefügt
- `DESCRIPTION.md`: Kurzbeschreibung (DE/EN, für Repository "About"),
  Topics, Beschreibung und Links (Eisberg Tech `https://eisberg-tech.de`,
  GitHub-Repository, Releases, Issues). In `.gitignore` per
  `!DESCRIPTION.md` freigegeben.
- `013_build_pyinstaller.sh`, `014_build_nuitka.sh` (Basis: sh_create-Templates
  v1.1): Version aus `CHANGELOG.md` (Fallback-Menü bzw. `--fallback-version`,
  Suffix `_no-changelog`), Python der `.venv` je Plattform (Linux
  `.venv/bin/python`, Git Bash unter Windows `.venv/Scripts/python.exe`),
  Nachinstallation des gepinnten Build-Werkzeugs aus `requirements-dev.txt`,
  `xvfb-run -a` ohne Display, Nuitka-Vorprüfung `gcc`/`patchelf` unter Linux.
  Paket-/Daten-Flags in `BUILD_ARGS` (`controllers`, `models`, `services`,
  `.env.example`), Aufruf `build.py <target> --version X.Y.Z --tool-arg=...`.
- `build.py`: Option `--version X.Y.Z` (Windows: PyInstaller
  `--version-file build/version_info.txt`, Nuitka `--product-name`,
  `--product-version`, `--file-version` = `X.Y.Z.0`; Linux ohne Wirkung) und
  `--tool-arg=FLAG` (mehrfach, an PyInstaller/Nuitka durchgereicht).

### Geändert
- `README.md` überarbeitet: Inhaltsverzeichnis, Voraussetzungen je Plattform,
  Abschnitt Desktop-Builds, Skript-Tabelle auf die vorhandenen `.sh`-Skripte
  (statt der entfernten `.ps1`-Skripte), Links.
- `INFRA.md` (Linux-Build, Betriebs-Skripte) und `MVC.md` (Skript-Zeilen) auf
  `.sh`-Skripte umgestellt.
- Version 1.4.1: `static/index.html` (Über), `android/app/build.gradle.kts`
  Default `versionName`/`versionCode` (10401).

### Verifiziert
- `./013_build_pyinstaller.sh --no-pause` unter Linux (Debian 13, Python
  3.13, PyInstaller 6.22.3): Build ok, Selftest exit 0, keine
  Laufzeit-Dateien, `.env.example` im Bundle; Exit 0.
- `./014_build_nuitka.sh --no-pause`: Nuitka 4.2.2 nachinstalliert,
  Vorprüfung bricht ohne `patchelf` mit Hinweis ab (Exit 1). Vollständiger
  Nuitka-Build auf diesem Host nicht gelaufen (patchelf nicht installiert).
- Windows-Pfad nur simuliert: Versionsflags und `version_info.txt`
  (`filevers=(1, 4, 1, 0)`) geprüft; kein Build unter Windows gelaufen.
- `pytest -q`: 228 passed.

## [1.4.0] - 2026-11-18
### Hinzugefügt
- Zwei Layouts nach Eisberg-Tech-CI (L6), produktiv in `static/`: A "Werkbank"
  (Desktop: Seitenleiste mit Zeichen, Navigation, "Zuletzt"-Liste und
  Verbindung, zweispaltiger Arbeitsbereich; ab 900 px Fensterbreite und darunter
  64-px-Schiene. Android: App-Leiste, Karten-Feed, Bottom-Navigation,
  Eingabezeile der Rückfrage über der Navigation, Historie-Detail als Blatt von
  unten) und B "Fokus" (Desktop: Kopfzeile mit Tabs und Verbindung, zentrierte
  Wizard-Karte 720 px, Historie Master-Detail. Android: App-Leiste mit
  Historie/Einstellungen bzw. Zurück, Fortschrittsbalken, ein Schritt pro
  Bildschirm, feste Hauptaktion unten). Umschaltung über `data-layout` am
  Root-Element, Desktop/Android über `(pointer: coarse), (max-width: 600px)`.
- Einstellung `LAYOUT` (`werkbank` | `fokus`) in `.env`:
  `services/settings.py` `LAYOUTS`, `DEFAULT_LAYOUT`, `load_layout(path,
  platform)`, `save_layout`. Ohne gesetzten Wert gilt der Plattform-Standard:
  Desktop `werkbank`, Android `fokus`.
- `controllers/api.py`: `set_layout` (Fehlertext `Ungueltiges Layout.`),
  `get_settings` liefert zusätzlich `layout`; `Api(..., platform="desktop")`,
  `android_entry.create_api` übergibt `platform="android"` explizit.
  `set_layout` in der Android-Whitelist.
- Einstellungen -> Darstellung: Umschalter "Layout: Werkbank / Fokus", wirkt
  sofort, persistiert per `set_layout`. Modus und Anbieter-Typ als
  Segment-Umschalter (versteckte `<select>` `#theme`, `#layout`, `#api-type`
  bleiben Quelle).
- Einstellungen -> Über: Lockup `logo_hell.svg`/`logo_dunkel.svg` je Modus
  (144 px, Schutzraum 22 px), App-Version, Link
  `https://github.com/Nope-im-not-pro/PromptEngineer`. Öffnet im externen
  Browser: Desktop über neue API-Methode `open_url` (`webbrowser.open`, nur
  diese URL, sonst `Link nicht erlaubt.`), Android über
  `PyBridge.open_url` (`@JavascriptInterface`, `Intent.ACTION_VIEW`, nur
  diese URL, sonst `false`). `shouldOverrideUrlLoading` unverändert.
- `static/fonts/` (Instrument Serif, Inter, JetBrains Mono, OFL) und
  `static/assets/` (Logos, Favicons) als Kopie aus `design/`; `@font-face`
  relativ, `<link rel="icon" href="assets/favicon.svg">`.
- `design/`: zwei Layout-Entwürfe nach Eisberg-Tech-CI (L6), je Desktop und
  Android als statische Mockups, Hell/Dunkel, Übersicht `design/index.html`.
  Logos, Favicons und Schriften als Kopie aus dem CI-Ordner. Bleibt
  unverändert als Referenz, nicht ausgeliefert.
- `.claude/launch.json`: lokaler Vorschau-Server `design-mockups`
  (127.0.0.1:8790).
- Tests: `tests/test_settings.py` (Layout laden/speichern/ungültig/Default je
  Plattform), `tests/test_api.py` (`set_layout`, Default je Plattform,
  `open_url` erlaubt/abgelehnt/Browser-Fehler), `tests/test_android_entry.py`
  (Default `fokus`, `set_layout`-Roundtrip, `open_url` nicht dispatchbar).
  `SelfTest.kt`: `layoutDefaultFokus`, `setLayoutRoundtrip`,
  `openUrlForeignRejected`.

### Geändert
- `static/index.html`, `app.css`, `app.js` neu aufgebaut. Alle bisherigen
  Element-IDs und Funktionen bleiben; `#error`, `#busy`, `#first-run` sind
  jetzt Statusboxen (Fehlertext in `#error-text`). Farben nur CI-Palette plus
  die in `design/ci_tokens.css` kommentierten Mischwerte und Fehlerfarben;
  Schriften Instrument Serif / Inter / JetBrains Mono. UI-Texte mit Umlauten.
- `--bg` hell `#F4FAFE`, dunkel `#062030`; Android `app_bg` (Fenster, Splash,
  Systemleisten-Grund) gleichgezogen, `SelfTest.kt` `BG_LIGHT`/`BG_DARK`.
- "Zuletzt"-Liste (Werkbank-Desktop) lädt `history_list` nur bei fertigen
  Einstellungen, damit `--selftest` keine `history.db` anlegt.
- `versionName` 1.4.0, `versionCode` 10400.
- Fehlerfarben (hell `#8E2A2A` auf `#FBEAEA`, Linie `#D9A3A3`; dunkel
  `#F2B8B8` auf `#3A1A24`, Linie `#8E4A55`), nicht CI-geregelt, vom Nutzer
  freigegeben (2026-11-18); Kommentar in `static/app.css`.
- `.gitignore`: `.taste-skill/` (lokaler Zustand Design-Werkzeug).

### Verifiziert
- taste-lint `design/`: 0 FAIL, 16 WARN (15x Mono-Schrift = CI-Vorgabe
  JetBrains Mono, 1x Inset-Rahmen gewählte Antwortvorgabe).
- pytest: 228 passed. `python main.py --selftest`: Exit 0.
- pywebview-Lauf (GTK, hidden): Default `werkbank` bei frischer `.env`,
  Umschalten auf `fokus` sofort, nach Neustart erhalten; Repo-Link ruft
  `webbrowser.open` genau mit der Repo-URL, fremde URL abgelehnt; `app.css`,
  `app.js`, `assets/*`, `fonts/*` liefern 200.
- Android (Emulator Pixel 8, API 34): `connectedDebugAndroidTest` 12/12 grün
  (inkl. `layoutDefaultFokus`, `setLayoutRoundtrip`, `openUrlForeignRejected`);
  Asset-Requests `/assets/static/fonts/*` und `/assets/static/assets/*` 200;
  Klick auf den Repo-Link öffnet den System-Browser (Chrome).
- Sichtprüfung In-App-Browser-Pane: Werkbank und Fokus, Hell und Dunkel, bei
  1100x720, 800x600 und 360x800, alle drei Tabs; Touch-Ziele mobil >= 48 px.

## [1.3.0] - 2026-10-04
### Hinzugefuegt
- Android-App (`UMSETZUNGSPLAN_ANDROID.md`, T1-T7): Projekt `android/`
  (Gradle 9.4.1, AGP 9.2.1, Chaquopy 17.0.0 / Python 3.11, compileSdk/targetSdk
  36, minSdk 26, ABIs arm64-v8a + x86_64, Paket `de.nopeimnotpro.promptengineer`,
  versionName 1.3.0). Bestehende Python-Schichten + `static/` laufen unveraendert
  in Chaquopy + WebView (WebViewAssetLoader, Origin
  `https://appassets.androidplatform.net`).
- `android_entry.py`: Android-Einstieg, Dispatcher `dispatch(method, args_json)`
  auf `controllers.api.Api`, Laufzeit-Dateien (`.env`, `history.db`, `app.log`)
  im App-Datenordner, Logging `basicConfig(force=True)`.
- `android/app/src/main/assets/bridge.js`: Shim `window.pywebview.api.*` ->
  `AndroidBridge.call`; `PyBridge.kt` (Single-Thread-Executor, Fehlertext
  `Interner Fehler (Bruecke).`, `copy_text` fuer die Zwischenablage).
- Dark-Mode Desktop + Android: Einstellungen -> Darstellung (System / Hell /
  Dunkel), Schluessel `THEME` in `.env`; `get_settings` liefert `theme`,
  neue API-Methode `set_theme`, Fehlertext `Ungueltiger Darstellungsmodus.`
  Android: AppCompat-DayNight, Systemleisten-Farbe je Modus, Edge-to-Edge mit
  Insets.
- App-Icon (Adaptive Icon inkl. Monochrom) und Splash-Logo `splash_icon.xml`
  (Entwurf Mimo, Nutzerwahl). Splash bis `onPageFinished`.
- Android-Haertung: `shouldOverrideUrlLoading` blockt fremde Navigation,
  Nicht-Asset-Requests -> 403, Backup-Regeln ohne `.env`/`history.db`/`app.log`,
  R8-Regel fuer `@JavascriptInterface`.
- Instrumentation-Tests `SelfTest.kt` (9 Tests) und `tests/test_android_entry.py`
  (22 Tests).
- `005_build_apk.ps1` (lokal, `*.ps1` gitignored; Plan Android T7 Chunk 1):
  `-Variant debug|release` (Default debug), `-Install`. Prueft
  `android\gradlew.bat`, JAVA_HOME, SDK (ANDROID_HOME oder `sdk.dir` aus
  `android\local.properties`), `py -3.11`, `versionName` aus
  `android\app\build.gradle.kts`; ruft `assembleDebug`/`assembleRelease`,
  reicht Gradle-Exit-Code durch; Kopie nach
  `dist\android\PromptEnginEEr-<versionName>-<variant>.apk`, Release ohne
  `android\keystore.properties` -> `-release-debugsigned.apk` + Warnung.
  `-Install`: `adb install -r`, Abbruch bei != 1 Geraet.
  `keystore.properties` nur per `Test-Path`, nie gelesen.
  `-Install` mit `adb -s <serial>`; `sdk.dir`-Fallback auch bei ANDROID_HOME
  auf nicht vorhandenen Pfad.
- `006_build_linux.ps1` (lokal, gitignored): Linux-Build x86_64 vom
  Windows-Host ueber Docker Desktop (Ubuntu 24.04, `python3-gi`, WebKit2GTK
  4.1, Python 3.12 venv `--system-site-packages`). `-Target
  pyinstaller|nuitka|all`, ruft unveraendertes `build.py` je Target unter
  `xvfb-run -a`, Version aus CHANGELOG (Fallback `_no-changelog`), Ausgabe
  `dist\linux\PromptEnginEEr-<version>-linux-x86_64-<target>.tar.gz` nur bei
  gruenem Selftest, Logs `dist\linux\logs\`. Quelle read-only gemountet, ohne
  `.env`/`history.db`/`app.log`/`.venv`/`android`/`z_*`.
### Geaendert
- View (`static/`): Farb-Token als CSS-Variablen, Dark-Block per
  `prefers-color-scheme` und `data-theme`; neue Token `--primary-bg`,
  `--border-strong`, `--border-faint`; Schrittleisten-Text nutzt `--muted`;
  Mobile-Layout (viewport, Media-Queries), Tastatur-Hinweis nur Desktop.
- `--border-input` fuer Kontrast >= 3:1 (UI-Kontrast, Plan R8): hell
  `#bbb` -> `#888`, dunkel `#555` -> `#707070`.
- `static/app.js`: `copyText` nutzt auf Android `AndroidBridge.copy_text`
  (WebView 69 auf API 26 schreibt sonst nicht in die Zwischenablage);
  `setBusy` sperrt auch `#theme`.
### Behoben
- Android, Modus Dunkel bei hellem Geraet (Kaltstart): heller System-Splash (F1)
  und helle Systemleisten mit hellen Icons (F2). `MainActivity` setzt den Modus
  in `attachBaseContext` vor `super`, ab API 31 zusaetzlich
  `UiModeManager.setApplicationNightMode`, Systemleisten ueber
  `enableEdgeToEdge(SystemBarStyle.auto)`.
### Verifiziert
- `pytest -q` 179 passed; `main.py --selftest` Exit 0; `build.py all` Exit 0
  (PyInstaller 8,5 MB, Nuitka 20,5 MB, beide Selftest gruen).
- `gradlew assembleDebug assembleRelease assembleDebugAndroidTest` Exit 0;
  APK debug 41,27 MB, release-debugsigned 35,58 MB.
- `connectedDebugAndroidTest` API 36: 9 Tests, 0 Fehler, 0 Skips.
  API 26 (WebView/Chrome 69): 9 Tests, 0 Fehler, 1 Skip
  (`systemModeFollowsUiMode`, WebView ohne `prefers-color-scheme`).
- Release-Bruecken-Smoke API 36 + API 26 ohne Bruecken-/Skriptfehler;
  Agent-Smoke API 36 (Start, Modus, Tastatur, Netzfehler-Klartext) gruen;
  Kaltstart-Szenarien Dunkel/Hell/System API 36 ohne Fremd-Frame.
- `005_build_apk.ps1`: PS-Parser 0; debug/release Exit 0; `-Install` am
  Emulator Exit 0.
- App-Icon/Splash: `gradlew assembleDebug testDebugUnitTest` Exit 0; Sichtpruefung
  am Geraet offen (kein Emulator aktiv).
- `006_build_linux.ps1 -Target all`: PS-Parser 0; Exit 0 (793 s). PyInstaller
  78 s, Programmdatei 5,5 MB, Archiv 35,2 MB; Nuitka 670 s, Programmdatei
  32,0 MB, Archiv 15,9 MB; beide Selftests unter xvfb Exit 0, `leaked=[]`.

## [1.2.0] - 2026-10-03
### Hinzugefuegt
- Codeberg-Push-Skripte (lokal, `*.ps1` gitignored), Remote `codeberg` ->
  `https://codeberg.org/Nope-im-not-pro/PromptEnginEEr.git`:
  `020_codeberg_push.ps1`, `021_codeberg_push_forced.ps1`
  (`--force-with-lease`, Bestaetigung `FORCE`),
  `022_codeberg_push_wipe_history.ps1` (verwaister Commit, `--force`,
  Bestaetigung `WIPE HISTORY`, lokales `.git` und `origin` bleiben erhalten).
### Verifiziert
- PS-Parser: 0 Fehler in 020-022.
- Lokaler Test gegen Bare-Repos (Codeberg-URL umgebogen, kein echter Push):
  020 Erst-/Folge-Push Exit 0; 021 bei unbekanntem Remote-Stand Exit 1
  (`stale info`), nach `fetch` Exit 0; 022 -> Remote genau 1 Commit, lokale
  Historie, GitHub-Bare und `origin` unveraendert; 021 nach 022 stellt volle
  Historie her; 022 mit falscher Bestaetigung Exit 1, Remote unveraendert.

## [1.1.0] - 2026-10-03
### Hinzugefuegt
- Betriebs-Skripte (lokal, `*.ps1` gitignored): `000_app_common.ps1`,
  `001_install.ps1`, `002_build.ps1`, `003_start.ps1`, `004_stop.ps1`;
  PowerShell 5.1 (Windows) und 7 (Linux).
- Linux-Unterstuetzung in `build.py`: `os.pathsep` fuer `--add-data`,
  Programmdatei ohne `.exe`, MSVC-/pythonnet-Flags nur unter Windows.
### Verifiziert
- PS-Parser: 0 Fehler in allen fuenf Skripten.
- `001_install.ps1` auf bestehender `.venv` -> Exit 0, Python 3.11.9.
- `002_build.ps1 -Target all` -> PyInstaller 8,5 MB/29 s, Nuitka 20,5 MB/441 s,
  beide `--selftest` Exit 0, dist ohne Laufzeit-Dateien; Windows-Flags
  identisch zu 1.0.1. Mit laufender App -> Exit 1 (dist gesperrt).
- `003_start.ps1` / `004_stop.ps1` in pyinstaller, nuitka, source, auto:
  Start, Doppelstart-Sperre, sanfter Stop, Stop ohne Instanz -> Exit 0.
- `pytest -q` -> 135 passed.
- Linux-Pfad nicht ausgefuehrt (keine Linux-Umgebung), nur Parser-Check.

## [1.0.1] - 2026-10-03
### Behoben
- `services/settings.py`: `.env` wird ohne `${VAR}`-Interpolation geladen
  (`interpolate=False`); Keys mit `${...}` bleiben woertlich, keine
  Umgebungsvariablen oder fremden `.env`-Werte im Key.
### Geaendert
- `UMSETZUNGSPLAN.md` 1.6: Extractor-Text an Umsetzung angeglichen (erstes `{`
  bis letztes `}`, Fences im optimierten Prompt bleiben erhalten).
- ERKLAERUNG: Interpolation, Plan-1.6-Abgleich.
### Verifiziert
- `.venv\Scripts\python -m pytest -q` -> 135 passed (3 neue Tests, vor Fix rot).
- `build.py all` -> PyInstaller 8,5 MB/37 s, Nuitka 20,5 MB/481 s, beide
  `--selftest` Exit 0, dist ohne `.env`/`history.db`/`app.log`.

## [1.0.0] - 2026-10-03
### Hinzugefuegt
- `.venv` Python 3.11.9, `requirements.txt` (pywebview, httpx, python-dotenv),
  `requirements-dev.txt` (pytest, PyInstaller, Nuitka), `pytest.ini`.
- `services/paths.py`: `app_dir`, `resource_dir`, `env_path`, `db_path`
  (Dev, PyInstaller, Nuitka).
- `services/settings.py`: `.env` laden/speichern (`set_key`), Validierung,
  Key-Maskierung.
- `services/providers.py`: OpenAI-/Anthropic-Adapter, Modellliste mit Paging,
  Chat, deutsche `ProviderError`-Meldungen, Key nur ASCII.
- `models/history.py`: SQLite-Historie (Sessions, Turns, CASCADE).
- `services/optimizer.py`: System-Prompt, JSON-Protokoll `clear`/`unclear`,
  Reparatur-Retry, `require_clear` nach Option-Wahl.
- `controllers/api.py`: pywebview `js_api` (Einstellungen, Modelle,
  Optimieren, Option, Neu formulieren, Historie); Key nur an gespeicherten
  Host, abgeschlossene Sitzung nicht fortsetzbar.
- `static/` (index.html, app.css, app.js): Tabs Optimieren/Historie/
  Einstellungen, Schrittleiste, Erststart -> Einstellungen, nach erstem
  Speichern -> Optimieren; nur `textContent`, keine externen Ressourcen.
- `main.py`: Start, Fehler-Log `app.log`, `--selftest` ohne Laufzeit-Dateien.
- `build.py`: PyInstaller `--onedir` und Nuitka `--standalone` (MSVC),
  anschliessend Selftest der exe.
- Build-Spike `z_spike\` mit `SPIKE_BEFUND.md`.
### Geaendert
- README, INFRA, MVC, ERKLAERUNG vom Plan- auf Umsetzungsstand.
### Verifiziert
- `.venv\Scripts\python -m pytest -q` -> 132 passed (ohne Netz, ohne echte `.env`).
- `main.py --selftest` -> Exit 0.
- `dist\pyinstaller\PromptEnginEEr\PromptEnginEEr.exe --selftest` -> Exit 0.
- `dist\nuitka\PromptEnginEEr\PromptEnginEEr.exe --selftest` -> Exit 0.
- Beide dist-Ordner ohne `.env`, `history.db`, `app.log`.
- Review je Teilaufgabe T1-T8 ohne Befund.

## [0.1.1] - 2026-10-03
### Hinzugefuegt
- Push-Skripte `010_github_push.ps1`, `011_github_push_forced.ps1`
  (`--force-with-lease`, Bestaetigung `FORCE`), `012_github_push_wipe_history.ps1`
  (neues `.git`, ein Initial-Commit, `--force`, Bestaetigung `WIPE HISTORY`).
  Ziel `https://github.com/Nope-im-not-pro/Prompt_EnginEEr_v2`, Branch `main`.
### Behoben
- `.gitignore`: `.env*` (ausser `.env.example`), `history.db*` (inkl. SQLite
  `-journal`/`-wal`/`-shm`), `app.log`, `.venv/`, `__pycache__/`,
  `.pytest_cache/`, `build/`, `dist/`, `*.spec`, `nuitka-crash-report.xml`,
  `.vscode/`, `.idea/`, `.claude/`, `Thumbs.db`, `desktop.ini` ergaenzt
  (INFRA.md nannte `.env` bereits als gitignored).
### Verifiziert
- PowerShell-Parser: 0 Fehler in allen drei Skripten.
- `.gitignore` gegen Dummy-Dateisatz: Secrets/DB/Logs/Build-/Editor-Reste
  ignoriert; `.env.example`, `build.py`, Quellcode, `static/`, `tests/` werden
  hochgeladen.

## [0.1.0] - 2026-10-02
### Hinzugefuegt
- Initiales Scaffold (project: Prompt_EnginEEr_v2) via std-workflow.

