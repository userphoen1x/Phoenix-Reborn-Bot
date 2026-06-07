from core.constants import TIME_UNITS_MAP, IMPLICIT_TIME_MAP

class ModerationService:
    @staticmethod
    def parse_punish_data(cmd: str, clean_parts: list) -> tuple[int | None, str, str]:
        parsed_minutes = None
        time_str = "10 минут"
        reason_parts = []

        if cmd in ["бан", "ban"]:
            parsed_minutes = 0
            time_str = "навсегда"
            reason_parts = clean_parts
        elif cmd in ["мут", "mute"] and clean_parts:
            first_word = clean_parts[0].lower()
            if first_word in IMPLICIT_TIME_MAP:
                parsed_minutes = IMPLICIT_TIME_MAP[first_word]
                reason_parts = clean_parts[1:]
            elif any(first_word.endswith(s) and first_word[:-len(s)].isdigit() for s in TIME_UNITS_MAP.keys()):
                for suffix, multiplier in sorted(TIME_UNITS_MAP.items(), key=lambda x: len(x[0]), reverse=True):
                    if first_word.endswith(suffix):
                        val_str = first_word[:-len(suffix)]
                        if val_str.isdigit():
                            parsed_minutes = int(val_str) * multiplier
                            reason_parts = clean_parts[1:]
                            break
            elif first_word.isdigit():
                val = int(first_word)
                if len(clean_parts) > 1:
                    second_word = clean_parts[1].lower()
                    matched_multiplier = None
                    for suffix, multiplier in sorted(TIME_UNITS_MAP.items(), key=lambda x: len(x[0]), reverse=True):
                        if second_word == suffix or second_word.startswith(suffix):
                            matched_multiplier = multiplier
                            break
                    if matched_multiplier:
                        parsed_minutes = val * matched_multiplier
                        reason_parts = clean_parts[2:]
                    else:
                        parsed_minutes = val
                        reason_parts = clean_parts[1:]
                else:
                    parsed_minutes = val
                    reason_parts = clean_parts[1:]
            else:
                reason_parts = clean_parts

        if cmd in ["мут", "mute"] and parsed_minutes is None:
            parsed_minutes = 10

        reason = " ".join(reason_parts) if reason_parts else "Не указана"

        if parsed_minutes == 0:
            time_str = "навсегда"
        elif parsed_minutes is not None:
            m = parsed_minutes
            if m < 60:
                if m % 10 == 1 and m % 100 != 11: time_str = f"{m} минуту"
                elif 2 <= m % 10 <= 4 and not (12 <= m % 100 <= 14): time_str = f"{m} минуты"
                else: time_str = f"{m} минут"
            elif m < 1440:
                h = m // 60
                if h % 10 == 1 and h % 100 != 11: time_str = f"{h} час"
                elif 2 <= h % 10 <= 4 and not (12 <= h % 100 <= 14): time_str = f"{h} часа"
                else: time_str = f"{h} часов"
            else:
                d = m // 1440
                if d % 10 == 1 and d % 100 != 11: time_str = f"{d} день"
                elif 2 <= d % 10 <= 4 and not (12 <= d % 100 <= 14): time_str = f"{d} дня"
                else: time_str = f"{d} дней"

        return parsed_minutes, time_str, reason