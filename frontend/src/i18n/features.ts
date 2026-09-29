// Названия удобств по кодам бэкенда (TASK-018): furniture, air_conditioning, ...
// Отдельным файлом, а не в strings.ts — чтобы не пересекаться с параллельными правками словаря.
// Неизвестный код не показывается (а не выводится как есть по-английски).

import type { Lang } from './strings';

const FEATURES: Record<Lang, Record<string, string>> = {
  ka: {
    furniture: 'ავეჯი',
    furnished: 'ავეჯით',
    kitchen_appliances: 'სამზარეულო ტექნიკით',
    air_conditioning: 'კონდიციონერი',
    heating: 'გათბობა',
    hot_water: 'ცხელი წყალი',
    washing_machine: 'სარეცხი მანქანა',
    dishwasher: 'ჭურჭლის სარეცხი მანქანა',
    fridge: 'მაცივარი',
    tv: 'ტელევიზორი',
    internet: 'ინტერნეტი',
    gas: 'ბუნებრივი აირი',
    elevator: 'ლიფტი',
    parking: 'პარკინგი',
    balcony: 'აივანი',
    storage: 'სათავსო',
    pool: 'აუზი',
    pets_allowed: 'შინაური ცხოველები დაშვებულია',
    security: 'დაცვა',
  },
  ru: {
    furniture: 'Мебель',
    furnished: 'С мебелью',
    kitchen_appliances: 'Кухня с техникой',
    air_conditioning: 'Кондиционер',
    heating: 'Отопление',
    hot_water: 'Горячая вода',
    washing_machine: 'Стиральная машина',
    dishwasher: 'Посудомоечная машина',
    fridge: 'Холодильник',
    tv: 'Телевизор',
    internet: 'Интернет',
    gas: 'Газ',
    elevator: 'Лифт',
    parking: 'Парковка',
    balcony: 'Балкон',
    storage: 'Кладовая',
    pool: 'Бассейн',
    pets_allowed: 'Можно с животными',
    security: 'Охрана',
  },
  en: {
    furniture: 'Furniture',
    furnished: 'Furnished',
    kitchen_appliances: 'Kitchen appliances',
    air_conditioning: 'Air conditioning',
    heating: 'Heating',
    hot_water: 'Hot water',
    washing_machine: 'Washing machine',
    dishwasher: 'Dishwasher',
    fridge: 'Fridge',
    tv: 'TV',
    internet: 'Internet',
    gas: 'Gas',
    elevator: 'Elevator',
    parking: 'Parking',
    balcony: 'Balcony',
    storage: 'Storage room',
    pool: 'Pool',
    pets_allowed: 'Pets allowed',
    security: 'Security',
  },
};

/** Название удобства на языке интерфейса; undefined — код неизвестен */
export function featureName(code: string, lang: Lang): string | undefined {
  return (FEATURES[lang] ?? FEATURES.ru)[code];
}
