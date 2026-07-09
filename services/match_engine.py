import logging

from sheets import (
    find_girl_by_chat_id,
    get_girl_events_with_blanks,
    get_match_blanks_for_event,
    ws_girls,
)

log = logging.getLogger(__name__)

# Maps both single-letter codes AND full text to human-readable labels
_CODE_TO_LABEL = {
    "П": "подругу",
    "К": "колаборацію",
    "Б": "бізнес-партнера",
    "Т": "travel-партнера",
    "+": "більше спілкування",
    "?": "щось цікаве",
    "подруга": "подругу",
    "колаборація": "колаборацію",
    "бізнес": "бізнес-партнера",
    "travel": "travel-партнера",
    "хочу більше спілкуватись": "більше спілкування",
}


def _slot_to_reasons(slot_value: str) -> list[str]:
    """Parse a slot value (may contain multiple codes separated by comma) into reason labels."""
    reasons = []
    for part in slot_value.split(","):
        part = part.strip().lower()
        if not part:
            continue
        for key, label in _CODE_TO_LABEL.items():
            if key.lower() == part or part.startswith(key.lower()):
                if label not in reasons:
                    reasons.append(label)
                break
        else:
            if part and part not in reasons:
                reasons.append(part)
    return reasons


def find_mutual_matches(girl_id: str, event_name: str) -> list[dict]:
    blanks = get_match_blanks_for_event(event_name)
    if not blanks:
        return []

    my_blank = None
    for b in blanks:
        if str(b.get("ID дівчини", "")) == str(girl_id):
            my_blank = b
            break

    if not my_blank:
        return []

    my_number = int(my_blank.get("Номер на бланку", 0) or 0)
    if not my_number:
        return []

    my_slots = {}
    for i in range(1, 25):
        val = my_blank.get(f"Слот {i}", "").strip()
        if val:
            my_slots[i] = val

    girls_data = ws_girls.get_all_values()
    headers = girls_data[0]
    girl_profiles = {}
    for row in girls_data[1:]:
        d = dict(zip(headers, row))
        gid = d.get("ID", "")
        if gid:
            girl_profiles[str(gid)] = d

    matches = []
    for other_blank in blanks:
        other_id = str(other_blank.get("ID дівчини", ""))
        if other_id == str(girl_id):
            continue

        other_number = int(other_blank.get("Номер на бланку", 0) or 0)
        if not other_number:
            continue

        i_marked_her = my_slots.get(other_number)
        her_slot_for_me = other_blank.get(f"Слот {my_number}", "").strip()

        if i_marked_her and her_slot_for_me:
            profile = girl_profiles.get(other_id, {})

            reasons = set()
            reasons.update(_slot_to_reasons(i_marked_her))
            reasons.update(_slot_to_reasons(her_slot_for_me))

            matches.append({
                "girl_id": other_id,
                "name": profile.get("Імʼя", other_blank.get("Імʼя", "?")),
                "age": profile.get("Вік", ""),
                "occupation": profile.get("Чим займається", ""),
                "hobbies": profile.get("Хобі", ""),
                "instagram": profile.get("Instagram", ""),
                "tiktok": profile.get("TikTok", ""),
                "telegram": profile.get("Telegram username", ""),
                "match_reasons": list(reasons),
                "my_code": i_marked_her,
                "her_code": her_slot_for_me,
            })

    return matches
