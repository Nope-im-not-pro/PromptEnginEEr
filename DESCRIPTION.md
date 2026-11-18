# Prompt EnginEEr - Description

## Kurzbeschreibung (Repository "About", max. 350 Zeichen)

DE: Desktop- und Android-App, die frei formulierte Prompts per LLM in präzise,
kopierbare Prompts umwandelt. Eine gezielte Rückfrage bei Unklarheit,
OpenAI- und Anthropic-kompatible APIs (auch lokal, z. B. Ollama), Historie.
Ein Projekt von Eisberg Tech.

EN: Desktop and Android app that turns loosely written prompts into precise,
copy-ready prompts via an LLM. One targeted follow-up question when unclear,
OpenAI- and Anthropic-compatible APIs (local too, e.g. Ollama), history.
A project by Eisberg Tech.

Topics: `prompt-engineering`, `llm`, `openai`, `anthropic`, `ollama`,
`pywebview`, `android`, `chaquopy`, `desktop-app`, `python`

## Beschreibung

Prompt EnginEEr nimmt einen unbeholfen oder knapp formulierten Prompt entgegen
und liefert einen optimierten Prompt zurück. Ist die Absicht unklar, stellt das
Modell genau eine Rückfrage mit zwei bis fünf Antwortvorgaben; danach folgt das
Ergebnis. Anbieter, Basis-URL, API-Key und Modell sind frei wählbar, die
Modellliste wird automatisch vom Anbieter geladen.

- Plattformen: Windows 11, Linux (GTK/WebKit2), Android 8.0 bis 16.
- Oberfläche: zwei Layouts (Werkbank, Fokus), Hell/Dunkel/System.
- Daten bleiben lokal: Einstellungen in `.env`, Historie in SQLite.
- Builds: PyInstaller und Nuitka (Desktop), Gradle + Chaquopy (Android).

## Links

| Ziel | Link |
|---|---|
| Eisberg Tech (Herausgeber) | <https://eisberg-tech.de> |
| Quellcode (GitHub) | <https://github.com/Nope-im-not-pro/PromptEngineer> |
| Releases | <https://github.com/Nope-im-not-pro/PromptEngineer/releases> |
| Fehler melden / Wünsche | <https://github.com/Nope-im-not-pro/PromptEngineer/issues> |
| Änderungsverlauf | [CHANGELOG.md](CHANGELOG.md) |
| Projekt-Einstieg | [README.md](README.md) |
