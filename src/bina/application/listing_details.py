"""Подробности объявления: коды удобств, состояния и типа владельца (TASK-018).

Храним коды, а не текст сайта: интерфейс переводит их сам, поэтому на любом
языке приложения характеристики показываются на этом языке.
"""

# Удобства (фильтр «есть всё из списка»)
FEATURES: tuple[str, ...] = (
    "furniture",  # мебель
    "kitchen_appliances",  # кухня с техникой
    "air_conditioning",  # кондиционер
    "heating",  # отопление
    "hot_water",  # горячая вода
    "washing_machine",  # стиральная машина
    "dishwasher",  # посудомоечная машина
    "fridge",  # холодильник
    "tv",  # телевизор / ТВ
    "internet",  # интернет / Wi-Fi
    "gas",  # газ
    "elevator",  # лифт
    "parking",  # парковка / гараж
    "balcony",  # балкон / лоджия
    "storage",  # кладовая
    "pool",  # бассейн
    "pets_allowed",  # можно с животными
    "security",  # охрана / сигнализация
)

# Состояние квартиры
CONDITIONS: tuple[str, ...] = (
    "newly_renovated",  # новый / недавний ремонт
    "renovated",  # с ремонтом (старый, косметический)
    "needs_renovation",  # требует ремонта
    "under_renovation",  # идёт ремонт
    "white_frame",  # белый каркас
    "black_frame",  # чёрный каркас
    "green_frame",  # зелёный каркас
)

OWNER_TYPES: tuple[str, ...] = ("owner", "agent")


def clean_features(codes: list[str]) -> list[str]:
    """Только известные коды, без повторов, в порядке :data:`FEATURES`."""
    present = set(codes)
    return [code for code in FEATURES if code in present]
