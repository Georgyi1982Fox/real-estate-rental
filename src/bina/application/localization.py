# ruff: noqa: RUF001 - таблицы транслитерации: грузинские и кириллические буквы намеренно
"""Имена, адреса и районы на трёх языках без AI (TASK-019).

Имена людей и названия улиц не переводятся, а транслитерируются: «ნინო» →
«Нино» / «Nino». Тип улицы (ქუჩა, ул., St.) переводится словарём. Работает
мгновенно и бесплатно, результат одинаковый при каждом запросе.
"""

import re

LANGS: tuple[str, ...] = ("ka", "ru", "en")

_KA_LATIN = {
    "ა": "a", "ბ": "b", "გ": "g", "დ": "d", "ე": "e", "ვ": "v", "ზ": "z", "თ": "t",
    "ი": "i", "კ": "k", "ლ": "l", "მ": "m", "ნ": "n", "ო": "o", "პ": "p", "ჟ": "zh",
    "რ": "r", "ს": "s", "ტ": "t", "უ": "u", "ფ": "p", "ქ": "k", "ღ": "gh", "ყ": "q",
    "შ": "sh", "ჩ": "ch", "ც": "ts", "ძ": "dz", "წ": "ts", "ჭ": "ch", "ხ": "kh",
    "ჯ": "j", "ჰ": "h",
}  # fmt: skip
_KA_CYRILLIC = {
    "ა": "а", "ბ": "б", "გ": "г", "დ": "д", "ე": "е", "ვ": "в", "ზ": "з", "თ": "т",
    "ი": "и", "კ": "к", "ლ": "л", "მ": "м", "ნ": "н", "ო": "о", "პ": "п", "ჟ": "ж",
    "რ": "р", "ს": "с", "ტ": "т", "უ": "у", "ფ": "п", "ქ": "к", "ღ": "г", "ყ": "к",
    "შ": "ш", "ჩ": "ч", "ც": "ц", "ძ": "дз", "წ": "ц", "ჭ": "ч", "ხ": "х",
    "ჯ": "дж", "ჰ": "х",
}  # fmt: skip
_CYRILLIC_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
}  # fmt: skip
_CYRILLIC_KA = {
    "а": "ა", "б": "ბ", "в": "ვ", "г": "გ", "д": "დ", "е": "ე", "ё": "იო", "ж": "ჟ",
    "з": "ზ", "и": "ი", "й": "ი", "к": "კ", "л": "ლ", "м": "მ", "н": "ნ", "о": "ო",
    "п": "პ", "р": "რ", "с": "ს", "т": "ტ", "у": "უ", "ф": "ფ", "х": "ხ", "ц": "ც",
    "ч": "ჩ", "ш": "შ", "щ": "შჩ", "ъ": "", "ы": "ი", "ь": "", "э": "ე", "ю": "იუ",
    "я": "ია",
}  # fmt: skip

# Латинские имена (Davit, Mikheili): сначала двойные буквы, затем одиночные
_LATIN_DIGRAPHS = ("shch", "sh", "ch", "kh", "zh", "ts", "dz", "gh", "ph", "th")
_LATIN_CYRILLIC = {
    "shch": "щ", "sh": "ш", "ch": "ч", "kh": "х", "zh": "ж", "ts": "ц", "dz": "дз",
    "gh": "г", "ph": "ф", "th": "т",
    "a": "а", "b": "б", "c": "к", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "х",
    "i": "и", "j": "дж", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о", "p": "п",
    "q": "к", "r": "р", "s": "с", "t": "т", "u": "у", "v": "в", "w": "в", "x": "кс",
    "y": "й", "z": "з",
}  # fmt: skip
_LATIN_KA = {
    "shch": "შჩ", "sh": "შ", "ch": "ჩ", "kh": "ხ", "zh": "ჟ", "ts": "ც", "dz": "ძ",
    "gh": "ღ", "ph": "ფ", "th": "თ",
    "a": "ა", "b": "ბ", "c": "კ", "d": "დ", "e": "ე", "f": "ფ", "g": "გ", "h": "ჰ",
    "i": "ი", "j": "ჯ", "k": "კ", "l": "ლ", "m": "მ", "n": "ნ", "o": "ო", "p": "პ",
    "q": "ყ", "r": "რ", "s": "ს", "t": "ტ", "u": "უ", "v": "ვ", "w": "ვ", "x": "ქს",
    "y": "ი", "z": "ზ",
}  # fmt: skip
# Имя: одно слово с заглавной буквы (Davit). ВСЕ ЗАГЛАВНЫЕ или с цифрами — название компании
_LATIN_NAME_RE = re.compile(r"^[A-Z][a-z]+$")

_GEORGIAN_RE = re.compile("[\\u10a0-\\u10ff]")
_CYRILLIC_RE = re.compile("[\\u0400-\\u04ff]")


def script_of(text: str) -> str:
    """Язык по письменности: ``ka`` (грузинские буквы), ``ru`` (кириллица), иначе ``en``."""
    if _GEORGIAN_RE.search(text):
        return "ka"
    if _CYRILLIC_RE.search(text):
        return "ru"
    return "en"


_LATIN_RE = re.compile("[A-Za-z]")
# Меньше букв — язык не определить (номер дома, «2+1»): такой текст не проверяем
MIN_LETTERS = 3


def dominant_script(text: str) -> str | None:
    """Язык текста по большинству букв: ``ka``, ``ru`` или ``en``; ``None`` — букв почти нет.

    В отличие от :func:`script_of`, одно грузинское слово в русском тексте («район ვაკე»)
    не делает его грузинским: решает то, каких букв больше.
    """
    counts = {
        "ka": len(_GEORGIAN_RE.findall(text)),
        "ru": len(_CYRILLIC_RE.findall(text)),
        "en": len(_LATIN_RE.findall(text)),
    }
    language, letters = max(counts.items(), key=lambda item: item[1])
    return language if letters >= MIN_LETTERS else None


def in_language(text: str, language: str) -> bool:
    """Написан ли текст на ``language`` (короткий текст без букв — да)."""
    found = dominant_script(text)
    return found is None or found == language


def _map_chars(text: str, table: dict[str, str]) -> str:
    result: list[str] = []
    for char in text:
        lower = char.lower()
        if lower in table:
            mapped = table[lower]
            result.append(mapped.capitalize() if char != lower and mapped else mapped)
        else:
            result.append(char)
    return "".join(result)


def _capitalize_words(text: str) -> str:
    # В грузинском нет заглавных: после транслитерации — с заглавной каждое слово
    return re.sub(r"(^|[\s\-(«\"])(\w)", lambda m: m.group(1) + m.group(2).upper(), text)


def transliterate(text: str, target: str) -> str:
    """Текст буквами языка ``target`` (``ka``, ``ru``, ``en``); свой язык — без изменений."""
    source = script_of(text)
    if source == target or not text:
        return text
    if source == "ka":
        if target == "ru":
            # «ე» в начале слова звучит как «э»: ელენე → Элене
            text = re.sub(r"(^|[\s\-])ე", r"\1э", text)
            return _capitalize_words(_map_chars(text, _KA_CYRILLIC))
        return _capitalize_words(_map_chars(text, _KA_LATIN))
    if source == "ru":
        if target == "en":
            return _map_chars(text, _CYRILLIC_LATIN)
        # «ия» → «ია», а не «იია»: Мария → მარია
        text = re.sub("([иИ])я", r"\1а", text)
        return _map_chars(text, _CYRILLIC_KA)
    if target == "en":
        return text
    table = _LATIN_CYRILLIC if target == "ru" else _LATIN_KA
    return re.sub(
        r"[A-Za-z]+",
        lambda m: _latin_word(m.group(), table, capitalize=target == "ru"),
        text,
    )


def _latin_word(word: str, table: dict[str, str], *, capitalize: bool) -> str:
    """Латинское имя (Davit) → буквами ``table``; названия компаний (ВСЕ ЗАГЛАВНЫЕ) — как есть."""
    if not _LATIN_NAME_RE.match(word):
        return word
    lower, result, i = word.lower(), "", 0
    while i < len(lower):
        for size in (4, 2, 1):
            chunk = lower[i : i + size]
            if len(chunk) == size and chunk in table and (size == 1 or chunk in _LATIN_DIGRAPHS):
                result += table[chunk]
                i += size
                break
        else:
            result += lower[i]
            i += 1
    return result[:1].upper() + result[1:] if capitalize else result


def localize_name(name: str | None) -> dict[str, str]:
    """Имя человека или компании на трёх языках (транслитерация)."""
    if not name or not name.strip():
        return {}
    clean = re.sub(r"\s+", " ", name).strip()
    return {lang: transliterate(clean, lang) for lang in LANGS}


# ---------------------------------------------------------------- адреса

# Типы улиц: все написания → ключ; для каждого ключа — сокращение на каждом языке
_STREET_TYPES: dict[str, dict[str, str]] = {
    "street": {"ka": "ქ.", "ru": "ул.", "en": "St."},
    "avenue": {"ka": "გამზ.", "ru": "просп.", "en": "Ave."},
    "lane": {"ka": "შეს.", "ru": "пер.", "en": "Ln."},
    "dead_end": {"ka": "ჩიხი", "ru": "тупик", "en": "Dead End"},
    "square": {"ka": "მოედ.", "ru": "пл.", "en": "Sq."},
    "district": {"ka": "მ/რ", "ru": "мкр.", "en": "Microdistrict"},
    "highway": {"ka": "გზატკ.", "ru": "шоссе", "en": "Hwy"},
    "settlement": {"ka": "დას.", "ru": "пос.", "en": "Settlement"},
}
_STREET_WORDS: dict[str, str] = {
    "ქ": "street", "ქუჩა": "street", "ქუჩაზე": "street", "ул": "street", "улица": "street",
    "st": "street", "street": "street", "str": "street",
    "გამზ": "avenue", "გამზირი": "avenue", "просп": "avenue", "проспект": "avenue",
    "пр": "avenue", "ave": "avenue", "avenue": "avenue",
    "შეს": "lane", "შესახვევი": "lane", "пер": "lane", "переулок": "lane", "ln": "lane",
    "lane": "lane",
    "ჩიხი": "dead_end", "тупик": "dead_end",
    "მოედ": "square", "მოედანი": "square", "пл": "square", "площадь": "square", "sq": "square",
    "square": "square",
    "მ/რ": "district", "მიკრორაიონი": "district", "мкр": "district", "микрорайон": "district",
    "გზატკ": "highway", "გზატკეცილი": "highway", "шоссе": "highway", "hwy": "highway",
    "დას": "settlement", "დასახლება": "settlement", "пос": "settlement", "поселок": "settlement",
    "посёлок": "settlement",
}  # fmt: skip
_NUMBER_RE = re.compile(r"\d")


def _ka_nominative(word: str) -> str:
    """Родительный падеж грузинского названия → именительный: ცაგარელის → ცაგარელი."""
    if word.endswith("ძის"):
        return word[:-3] + "ძე"
    if word.endswith("ის") and len(word) > 3:
        return word[:-2] + "ი"
    if len(word) > 3 and word[-1] == "ს" and word[-2] in "აოუე":
        return word[:-1]
    return word


def localize_address(address: str | None) -> dict[str, str]:
    """Адрес («ცაგარელის ქ. 26», «ул. Мачабели 6») на трёх языках.

    Язык источника остаётся как на сайте; в остальных: тип улицы — словарём,
    название — транслитерацией (грузинское — в именительном падеже), номер — как есть.
    """
    if not address or not address.strip():
        return {}
    clean = re.sub(r"\s+", " ", address).strip(" ,")
    source = script_of(clean)
    kind: str | None = None
    names: list[str] = []
    numbers: list[str] = []
    for token in clean.replace(",", " ").split():
        key = token.lower().rstrip(".")
        if kind is None and key in _STREET_WORDS:
            kind = _STREET_WORDS[key]
        elif _NUMBER_RE.search(token):
            numbers.append(token)
        else:
            names.append(token)
    if source == "ka":
        names = [_ka_nominative(word) if len(word) > 2 else word for word in names]

    result: dict[str, str] = {}
    for lang in LANGS:
        if lang == source:
            result[lang] = clean
            continue
        name = " ".join(transliterate(word, lang) for word in names)
        street = _STREET_TYPES[kind][lang] if kind else ""
        parts = [street, name] if lang == "ru" else [name, street]
        result[lang] = " ".join(part for part in [*parts, *numbers] if part)
    return result


# ---------------------------------------------------------------- районы

# Районы Тбилиси и Батуми: (ru, en, ka) и другие написания с сайтов
_DISTRICTS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("Ваке", "Vake", "ვაკე", ()),
    ("Сабуртало", "Saburtalo", "საბურთალო", ()),
    ("Ваке-Сабуртало", "Vake-Saburtalo", "ვაკე-საბურთალო", ()),
    ("Мтацминда", "Mtatsminda", "მთაწმინდა", ()),
    ("Сололаки", "Sololaki", "სოლოლაკი", ()),
    ("Старый Тбилиси", "Old Tbilisi", "ძველი თბილისი", ("Старий Тбилиси",)),
    ("Вера", "Vera", "ვერა", ()),
    ("Дидубе", "Didube", "დიდუბე", ()),
    ("Дигоми", "Digomi", "დიღომი", ()),
    ("Дигомский массив", "Digomi Massive", "დიღმის მასივი", ("Дигомский Массив",)),
    ("Чугурети", "Chughureti", "ჩუღურეთი", ()),
    ("Дидубе-Чугурети", "Didube-Chughureti", "დიდუბე-ჩუღურეთი", ()),
    ("Надзаладеви", "Nadzaladevi", "ნაძალადევი", ()),
    ("Глдани", "Gldani", "გლდანი", ()),
    ("Глдани-Надзаладеви", "Gldani-Nadzaladevi", "გლდანი-ნაძალადევი", ()),
    ("Исани", "Isani", "ისანი", ()),
    ("Самгори", "Samgori", "სამგორი", ()),
    ("Исани-Самгори", "Isani-Samgori", "ისანი-სამგორი", ()),
    ("Крцаниси", "Krtsanisi", "კრწანისი", ()),
    ("Авлабари", "Avlabari", "ავლაბარი", ()),
    ("Ортачала", "Ortachala", "ორთაჭალა", ()),
    ("Абанотубани", "Abanotubani", "აბანოთუბანი", ()),
    ("Варкетили", "Varketili", "ვარკეთილი", ()),
    ("Лило", "Lilo", "ლილო", ()),
    ("Навтлуги", "Navtlughi", "ნავთლუღი", ()),
    ("Вазисубани", "Vazisubani", "ვაზისუბანი", ()),
    ("Мухиани", "Mukhiani", "მუხიანი", ()),
    ("Вашлиджвари", "Vashlijvari", "ვაშლიჯვარი", ()),
    ("Плато Нуцубидзе", "Nutsubidze Plateau", "ნუცუბიძის პლატო", ("Нуцубидзе плато",)),
    ("Багеби", "Bagebi", "ბაგები", ()),
    ("Цавкиси", "Tsavkisi", "წავკისი", ()),
    ("Табахмела", "Tabakhmela", "ტაბახმელა", ()),
    ("Кус Тба", "Turtle Lake", "კუს ტბა", ("Черепашье озеро",)),
    ("Лиси", "Lisi", "ლისი", ("Лиси озеро", "Лисий озеро")),
    ("Темка", "Temka", "თემქა", ()),
    ("Кукия", "Kukia", "კუკია", ()),
    ("Санзона", "Sanzona", "სანზონა", ()),
    ("Тбилисское море", "Tbilisi Sea", "თბილისის ზღვა", ()),
    ("Орхеви", "Orkhevi", "ორხევი", ()),
    ("Дидгори", "Didgori", "დიდგორი", ()),
    ("Тбилиси", "Tbilisi", "თბილისი", ()),
    # Батуми (TASK-079)
    ("Батуми", "Batumi", "ბათუმი", ("Районы Батуми",)),
    ("Старый Батуми", "Old Batumi", "ძველი ბათუმი", ("Старий Батуми",)),
    ("Новый бульвар", "New Boulevard", "ახალი ბულვარი", ("Новый Бульвар",)),
    ("Махинджаури", "Makhinjauri", "მახინჯაური", ()),
    ("Гонио", "Gonio", "გონიო", ()),
    ("Кахабери", "Kakhaberi", "კახაბერი", ()),
    ("Чакви", "Chakvi", "ჩაქვი", ()),
    ("Ангиса", "Angisa", "ანგისა", ()),
    ("Химшиашвили", "Khimshiashvili", "ხიმშიაშვილის უბანი", ("Район Химшиашвили",)),
)
_DISTRICT_INDEX: dict[str, tuple[str, str, str]] = {}
for _ru, _en, _ka, _aliases in _DISTRICTS:
    for _alias in (_ru, _en, _ka, *_aliases):
        _DISTRICT_INDEX[_alias.lower()] = (_ru, _en, _ka)


def district_names(name: str) -> dict[str, str]:
    """Название района на трёх языках: из словаря, иначе транслитерация.

    «Дигоми 3» → словарное «Дигоми» + номер.
    """
    clean = re.sub(r"\s+", " ", name or "").strip()
    if not clean:
        return {}
    match = re.match(r"^(.*?)(\s+\d+)?$", clean)
    base, suffix = (match.group(1), match.group(2) or "") if match else (clean, "")
    known = _DISTRICT_INDEX.get(base.lower())
    if known is not None:
        ru, en, ka = known
        return {"ru": ru + suffix, "en": en + suffix, "ka": ka + suffix}
    return {lang: transliterate(clean, lang) for lang in LANGS}
