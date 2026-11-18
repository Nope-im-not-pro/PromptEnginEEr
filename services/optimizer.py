"""Optimizer-Service: LLM-Protokoll (clear/unclear), Parser, Reparatur-Retry.

Plattformunabhaengig; chat_fn(system, messages) -> str wird injiziert.
"""
import json

SYSTEM_PROMPT = """Du bist ein Experte fuer Prompt-Engineering. Der Nutzer gibt einen frei und oft unbeholfen formulierten Roh-Prompt ein. Deine Aufgabe: daraus einen optimierten, direkt verwendbaren Prompt machen.

Vorgehen:
1. Analysiere die Absicht des Nutzers: Welche Aufgabenart ist gemeint und welches Zielergebnis soll entstehen?
2. Stelle nur bei echter Unklarheit zu Aufgabenart oder Zielergebnis eine Rueckfrage. Ist die Absicht erkennbar, liefere sofort den optimierten Prompt.
3. Eine Rueckfrage besteht aus genau einer Frage mit 2-5 Antwortoptionen. Kein Fragebogen, keine weiteren Fragen.
4. Der optimierte Prompt folgt Best Practice: Rolle, Kontext, Aufgabe, Vorgaben, Ausgabeformat und, falls hilfreich, Beispiele. Erfinde keine Fakten. Fehlende Angaben setzt du als [Platzhalter] ein.
5. Antworte in der Sprache des Nutzer-Prompts (Frage, Optionen und optimierter Prompt).

Antwortformat: Antworte ausschliesslich mit genau einem JSON-Objekt, ohne Zusatztext, ohne Markdown. Genau eines von:
{"status": "unclear", "question": "<Frage>", "options": [{"label": "<kurz>", "description": "<optional>"}]}
{"status": "clear", "optimized_prompt": "<optimierter Prompt>"}

Regeln: "options" hat 2-5 Eintraege, jedes "label" ist nicht leer. "optimized_prompt" ist nicht leer."""

REPAIR_MESSAGE = (
    "Deine letzte Antwort war ungueltig. Antworte nur mit gueltigem JSON nach dem "
    'Schema: {"status": "unclear", "question": "...", "options": '
    '[{"label": "...", "description": "..."}]} (2-5 Optionen) oder '
    '{"status": "clear", "optimized_prompt": "..."}. Kein Zusatztext.'
)

CLEAR_REPAIR_MESSAGE = (
    "Keine weitere Rueckfrage. Liefere jetzt den finalen optimierten Prompt, "
    'ausschliesslich als JSON: {"status": "clear", "optimized_prompt": "..."}'
)


class ProtocolError(Exception):
    pass


def start_message(raw_prompt: str) -> dict:
    return {"role": "user", "content": raw_prompt}


def choice_message(option: dict) -> dict:
    content = f"Gewaehlte Option: {option.get('label', '')}"
    if option.get("description"):
        content += f"\nBeschreibung: {option['description']}"
    content += (
        "\nLiefere jetzt den finalen optimierten Prompt, ohne weitere Rueckfrage, "
        'als JSON mit "status": "clear".'
    )
    return {"role": "user", "content": content}


def refine_message(refined_prompt: str) -> dict:
    return {"role": "user", "content": f"Neu formulierter Prompt:\n{refined_prompt}"}


def parse_response(text: str) -> dict:
    # Erstes "{" bis letztes "}" schliesst umschliessende Fences/Vor-/Nachtext aus;
    # Fences innerhalb von String-Werten bleiben unveraendert.
    cleaned = text or ""
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ProtocolError("Antwort enthaelt kein JSON")
    try:
        data = json.loads(cleaned[start:end + 1])
    except ValueError as exc:
        raise ProtocolError("Antwort ist kein gueltiges JSON") from exc
    if not isinstance(data, dict):
        raise ProtocolError("Antwort ist kein JSON-Objekt")

    status = data.get("status")
    if status == "clear":
        prompt = data.get("optimized_prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ProtocolError("optimized_prompt fehlt oder ist leer")
        return {"status": "clear", "optimized_prompt": prompt}
    if status == "unclear":
        question = data.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ProtocolError("question fehlt")
        options = data.get("options")
        if not isinstance(options, list) or not 2 <= len(options) <= 5:
            raise ProtocolError("options muss 2-5 Eintraege haben")
        parsed = []
        for opt in options:
            label = opt.get("label") if isinstance(opt, dict) else None
            if not isinstance(label, str) or not label.strip():
                raise ProtocolError("Option ohne label")
            desc = opt.get("description") or ""
            parsed.append({"label": label, "description": desc if isinstance(desc, str) else str(desc)})
        return {"status": "unclear", "question": question, "options": parsed}
    raise ProtocolError("unbekannter status")


def _check(text: str, require_clear: bool) -> dict:
    result = parse_response(text)
    if require_clear and result["status"] != "clear":
        raise ProtocolError("finaler Prompt erwartet, Rueckfrage erhalten")
    return result


def run_step(chat_fn, messages: list[dict], *,
             require_clear: bool = False) -> tuple[dict, str]:
    text = chat_fn(SYSTEM_PROMPT, list(messages))
    try:
        return _check(text, require_clear), text
    except ProtocolError:
        pass
    repair = CLEAR_REPAIR_MESSAGE if require_clear else REPAIR_MESSAGE
    retry = list(messages) + [
        {"role": "assistant", "content": text},
        {"role": "user", "content": repair},
    ]
    text = chat_fn(SYSTEM_PROMPT, retry)
    return _check(text, require_clear), text
