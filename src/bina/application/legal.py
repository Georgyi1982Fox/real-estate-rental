"""Пользовательское соглашение и политика конфиденциальности (TASK-089).

ЧЕРНОВИК: тексты составлены без юриста. Перед запуском их должен проверить
юрист в Грузии (закон «О защите персональных данных» 2023 г.), после чего
обновите ``VERSION``.

Документы показывает бот (``/terms``, ``/privacy``) и отдаёт API
(``GET /api/legal/{doc}``) — на языке пользователя.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

VERSION = date(2026, 9, 30)


class LegalDoc(StrEnum):
    TERMS = "terms"
    PRIVACY = "privacy"


@dataclass(frozen=True, slots=True)
class Section:
    title: str
    text: str


@dataclass(frozen=True, slots=True)
class LegalDocument:
    title: str
    intro: str
    sections: tuple[Section, ...]


VERSION_LABEL = {
    "ru": "Редакция от {date}",
    "en": "Version of {date}",
    "ka": "რედაქცია {date}",
}

_TERMS_RU = LegalDocument(
    title="Пользовательское соглашение Bina.ai",
    intro=(
        "Это соглашение действует между вами и сервисом Bina.ai (бот и мини-приложение "
        "в Telegram). Пользуясь сервисом, вы принимаете эти условия. Если вы с ними "
        "не согласны, пожалуйста, не пользуйтесь сервисом."
    ),
    sections=(
        Section(
            "1. Что делает сервис",
            "Bina.ai помогает искать жильё в аренду в Грузии: собирает публичные объявления "
            "с сайтов недвижимости, показывает их с переводом, проверками и подсказками, "
            "присылает уведомления о новых вариантах. Сервисом можно пользоваться с 18 лет.",
        ),
        Section(
            "2. Объявления",
            "Объявления публикуют третьи лица на своих сайтах; у каждого есть ссылка на "
            "оригинал. Bina.ai не является стороной сделки, не является агентом или "
            "собственником и не отвечает за точность объявлений, цены и наличие жилья. "
            "Перед оплатой всегда смотрите квартиру лично и проверяйте документы "
            "собственника. Никогда не переводите деньги до осмотра.",
        ),
        Section(
            "3. Оценки, проверки и документы",
            "Оценка цены, проверка на мошенничество, перевод, ответы ИИ-помощника, "
            "расчёт расходов и сведения о районах носят справочный характер и могут "
            "содержать ошибки. Договор аренды и акт приёмки — это шаблоны, заполненные "
            "вашими данными, а не юридическая консультация. Перед подписанием проверьте "
            "их сами или с юристом.",
        ),
        Section(
            "4. Premium и оплата",
            "Часть функций доступна по подписке Premium. Оплата — звёздами Telegram "
            "(Telegram Stars) внутри Telegram, данные карт мы не получаем. Подписка "
            "действует оплаченный срок и не продлевается сама. Если подписка не включилась "
            "или вы хотите вернуть оплату, напишите через команду /paysupport — мы "
            "рассмотрим запрос. Возврат звёзд выполняется средствами Telegram.",
        ),
        Section(
            "5. Правила",
            "Запрещено: использовать сервис для обмана, спама или мошенничества; "
            "автоматически собирать данные сервиса; отправлять заведомо ложные жалобы; "
            "мешать работе сервиса или обходить ограничения. За нарушения мы можем "
            "ограничить доступ к сервису.",
        ),
        Section(
            "6. Ответственность",
            "Сервис предоставляется «как есть». Мы стараемся, чтобы он работал без "
            "перерывов и ошибок, но не можем это гарантировать. Мы не отвечаем за "
            "решения, которые вы принимаете на основе объявлений и подсказок, и за "
            "действия собственников, агентов и других пользователей. Наша ответственность "
            "ограничена суммой, которую вы заплатили за Premium за последние 3 месяца.",
        ),
        Section(
            "7. Изменения и право",
            "Мы можем менять сервис и эти условия; о важных изменениях сообщим в боте. "
            "Продолжая пользоваться сервисом, вы принимаете новую редакцию. К соглашению "
            "применяется право Грузии. Вопросы — через команду /paysupport.",
        ),
    ),
)

_TERMS_EN = LegalDocument(
    title="Bina.ai Terms of Use",
    intro=(
        "These terms apply between you and the Bina.ai service (the Telegram bot and "
        "Mini App). By using the service you accept these terms. If you do not agree, "
        "please do not use the service."
    ),
    sections=(
        Section(
            "1. What the service does",
            "Bina.ai helps you find rental housing in Georgia: it collects public listings "
            "from real estate websites, shows them with translations, checks and tips, and "
            "notifies you about new matches. You must be 18 or older to use the service.",
        ),
        Section(
            "2. Listings",
            "Listings are published by third parties on their own websites; each one links "
            "to the original. Bina.ai is not a party to any deal, is not an agent or owner, "
            "and is not responsible for the accuracy of listings, prices or availability. "
            "Always view the apartment in person and check the owner's documents before "
            "paying. Never send money before a viewing.",
        ),
        Section(
            "3. Estimates, checks and documents",
            "Price estimates, fraud checks, translations, AI assistant answers, cost "
            "calculations and district information are for reference only and may contain "
            "mistakes. The lease agreement and the handover report are templates filled "
            "with your data, not legal advice. Check them yourself or with a lawyer before "
            "signing.",
        ),
        Section(
            "4. Premium and payments",
            "Some features require a Premium subscription. Payment is made in Telegram "
            "Stars inside Telegram; we never receive your card details. A subscription "
            "lasts for the paid period and does not renew automatically. If your "
            "subscription was not activated or you want a refund, contact us via the "
            "/paysupport command and we will review the request. Stars are refunded "
            "through Telegram.",
        ),
        Section(
            "5. Rules",
            "You must not: use the service for deception, spam or fraud; collect the "
            "service's data automatically; send knowingly false complaints; disrupt the "
            "service or bypass its limits. We may restrict access for violations.",
        ),
        Section(
            "6. Liability",
            "The service is provided “as is”. We try to keep it running without "
            "interruptions or errors but cannot guarantee that. We are not responsible for "
            "decisions you make based on listings and tips, or for the actions of owners, "
            "agents and other users. Our liability is limited to the amount you paid for "
            "Premium in the last 3 months.",
        ),
        Section(
            "7. Changes and governing law",
            "We may change the service and these terms; we will announce important changes "
            "in the bot. By continuing to use the service you accept the new version. "
            "These terms are governed by the laws of Georgia. Questions: use the "
            "/paysupport command.",
        ),
    ),
)

_TERMS_KA = LegalDocument(
    title="Bina.ai-ის სამომხმარებლო შეთანხმება",
    intro=(
        "ეს შეთანხმება მოქმედებს თქვენსა და სერვის Bina.ai-ს (ბოტი და მინი-აპლიკაცია "
        "ტელეგრამში) შორის. სერვისით სარგებლობით თქვენ ეთანხმებით ამ პირობებს. თუ არ "
        "ეთანხმებით, გთხოვთ, ნუ ისარგებლებთ სერვისით."
    ),
    sections=(
        Section(
            "1. რას აკეთებს სერვისი",
            "Bina.ai გეხმარებათ საქართველოში საქირავნო ბინის პოვნაში: აგროვებს საჯარო "
            "განცხადებებს უძრავი ქონების საიტებიდან, აჩვენებს მათ თარგმანით, შემოწმებებითა "
            "და რჩევებით, გიგზავნით შეტყობინებებს ახალ ვარიანტებზე. სერვისით სარგებლობა "
            "შეიძლება 18 წლიდან.",
        ),
        Section(
            "2. განცხადებები",
            "განცხადებებს მესამე პირები აქვეყნებენ საკუთარ საიტებზე; თითოეულს აქვს ბმული "
            "ორიგინალზე. Bina.ai არ არის გარიგების მხარე, აგენტი ან მესაკუთრე და არ აგებს "
            "პასუხს განცხადებების, ფასებისა და ბინის ხელმისაწვდომობის სიზუსტეზე. გადახდამდე "
            "ყოველთვის ნახეთ ბინა პირადად და შეამოწმეთ მესაკუთრის დოკუმენტები. არასოდეს "
            "გადარიცხოთ ფული დათვალიერებამდე.",
        ),
        Section(
            "3. შეფასებები, შემოწმებები და დოკუმენტები",
            "ფასის შეფასება, თაღლითობის შემოწმება, თარგმანი, ხელოვნური ინტელექტის ასისტენტის "
            "პასუხები, ხარჯების გაანგარიშება და ინფორმაცია უბნების შესახებ საცნობარო "
            "ხასიათისაა და შეიძლება შეიცავდეს შეცდომებს. ქირავნობის ხელშეკრულება და "
            "მიღება-ჩაბარების აქტი თქვენი მონაცემებით შევსებული შაბლონებია და არა "
            "იურიდიული კონსულტაცია. ხელმოწერამდე შეამოწმეთ ისინი თავად ან იურისტთან ერთად.",
        ),
        Section(
            "4. Premium და გადახდა",
            "ფუნქციების ნაწილი ხელმისაწვდომია Premium გამოწერით. გადახდა ხდება ტელეგრამის "
            "ვარსკვლავებით ტელეგრამის შიგნით; ბარათის მონაცემებს ჩვენ არ ვიღებთ. გამოწერა "
            "მოქმედებს გადახდილი ვადით და ავტომატურად არ გრძელდება. თუ გამოწერა არ "
            "ჩაირთო ან გსურთ თანხის დაბრუნება, მოგვწერეთ ბრძანებით /paysupport — "
            "განვიხილავთ მოთხოვნას. ვარსკვლავები ბრუნდება ტელეგრამის საშუალებით.",
        ),
        Section(
            "5. წესები",
            "აკრძალულია: სერვისის გამოყენება მოტყუებისთვის, სპამისთვის ან თაღლითობისთვის; "
            "სერვისის მონაცემების ავტომატური შეგროვება; შეგნებულად ცრუ საჩივრების გაგზავნა; "
            "სერვისის მუშაობისთვის ხელის შეშლა ან შეზღუდვების გვერდის ავლა. დარღვევისთვის "
            "შეიძლება შევზღუდოთ სერვისზე წვდომა.",
        ),
        Section(
            "6. პასუხისმგებლობა",
            "სერვისი მოწოდებულია „როგორც არის“. ვცდილობთ, რომ ის შეფერხებებისა და "
            "შეცდომების გარეშე მუშაობდეს, მაგრამ ამას ვერ გარანტირებთ. ჩვენ არ ვაგებთ "
            "პასუხს განცხადებებსა და რჩევებზე დაყრდნობით მიღებულ თქვენს გადაწყვეტილებებზე "
            "და მესაკუთრეების, აგენტებისა და სხვა მომხმარებლების ქმედებებზე. ჩვენი "
            "პასუხისმგებლობა შეზღუდულია თანხით, რომელიც ბოლო 3 თვეში Premium-ში გადაიხადეთ.",
        ),
        Section(
            "7. ცვლილებები და სამართალი",
            "შეიძლება შევცვალოთ სერვისი და ეს პირობები; მნიშვნელოვან ცვლილებებზე ბოტში "
            "გაცნობებთ. სერვისით სარგებლობის გაგრძელებით თქვენ ეთანხმებით ახალ რედაქციას. "
            "შეთანხმებაზე ვრცელდება საქართველოს კანონმდებლობა. კითხვები — ბრძანებით "
            "/paysupport.",
        ),
    ),
)

_PRIVACY_RU = LegalDocument(
    title="Политика конфиденциальности Bina.ai",
    intro=(
        "Здесь описано, какие данные собирает Bina.ai (бот и мини-приложение в Telegram), "
        "зачем, кому их передаёт и как их удалить."
    ),
    sections=(
        Section(
            "1. Какие данные мы храним",
            "Из Telegram: ваш идентификатор, имя, имя пользователя и язык. Из сервиса: "
            "избранное, сохранённые поиски и настройки уведомлений, история оплат Premium "
            "(сумма, дата, идентификатор платежа), жалобы на объявления, напоминания об "
            "аренде (дата и сумма), приглашения друзей, вопросы ИИ-помощнику и технические "
            "журналы. Номер телефона и данные карт мы не получаем.",
        ),
        Section(
            "2. Зачем",
            "Чтобы показывать подходящие объявления, присылать уведомления и напоминания, "
            "включать Premium, начислять бонусы за приглашения, бороться с мошенничеством "
            "и злоупотреблениями, исправлять ошибки и улучшать сервис.",
        ),
        Section(
            "3. Документы",
            "Имена, номера документов и другие данные, которые вы вводите в договор аренды "
            "или акт приёмки, используются только для создания файла. Файл отправляется "
            "вам, а сами данные мы не сохраняем.",
        ),
        Section(
            "4. Кому передаются данные",
            "Мы не продаём ваши данные. Их получают только сервисы, без которых Bina.ai не "
            "работает: Telegram (сообщения и оплата), поставщик ИИ-моделей (текст ваших "
            "вопросов помощнику и тексты объявлений — без вашего имени и идентификатора), "
            "Cloudflare (защита и доставка трафика) и хостинг, где работает сервер. "
            "Адреса объявлений (не ваши данные) переводятся в координаты через "
            "OpenStreetMap. Данные могут передаваться по закону по запросу государственных "
            "органов.",
        ),
        Section(
            "5. Сколько храним",
            "Пока вы пользуетесь сервисом. Резервные копии базы хранятся до 14 дней."
            " Данные об оплатах могут храниться дольше, если "
            "этого требует закон.",
        ),
        Section(
            "6. Ваши права",
            "Вы можете узнать, какие данные о вас хранятся, исправить их или попросить "
            "удалить всё. Напишите через команду /paysupport — ответим в течение 10 "
            "рабочих дней. Язык и уведомления можно изменить в /profile, избранное и "
            "поиски — удалить в самом сервисе.",
        ),
        Section(
            "7. Изменения",
            "Мы можем обновлять эту политику; о важных изменениях сообщим в боте. "
            "Политика применяется в соответствии с законодательством Грузии о защите "
            "персональных данных.",
        ),
    ),
)

_PRIVACY_EN = LegalDocument(
    title="Bina.ai Privacy Policy",
    intro=(
        "This policy explains what data Bina.ai (the Telegram bot and Mini App) collects, "
        "why, who receives it and how to delete it."
    ),
    sections=(
        Section(
            "1. What data we store",
            "From Telegram: your ID, name, username and language. From the service: "
            "favorites, saved searches and notification settings, Premium payment history "
            "(amount, date, payment ID), complaints about listings, rent reminders (date "
            "and amount), friend invitations, questions to the AI assistant and technical "
            "logs. We never receive your phone number or card details.",
        ),
        Section(
            "2. Why",
            "To show matching listings, send notifications and reminders, activate "
            "Premium, credit invitation rewards, fight fraud and abuse, fix errors and "
            "improve the service.",
        ),
        Section(
            "3. Documents",
            "Names, ID numbers and other details you enter into a lease agreement or "
            "handover report are used only to create the file. The file is sent to you, "
            "and we do not keep that data.",
        ),
        Section(
            "4. Who receives data",
            "We do not sell your data. It is shared only with services Bina.ai cannot work "
            "without: Telegram (messages and payments), the AI model provider (the text of "
            "your questions to the assistant and listing texts — without your name or ID), "
            "Cloudflare (protection and traffic delivery) and the hosting that runs the "
            "server. Listing addresses (not your data) are converted to coordinates via "
            "OpenStreetMap. Data may be disclosed to authorities when required by law.",
        ),
        Section(
            "5. How long we keep it",
            "While you use the service. Database backups are kept up to 14 days."
            " Payment records may be kept longer where the law requires it.",
        ),
        Section(
            "6. Your rights",
            "You can find out what data we hold about you, correct it or ask us to delete "
            "all of it. Contact us via the /paysupport command; we will reply within 10 "
            "business days. You can change the language and notifications in /profile and "
            "delete favorites and searches in the service itself.",
        ),
        Section(
            "7. Changes",
            "We may update this policy; we will announce important changes in the bot. "
            "The policy applies in accordance with the personal data protection laws of "
            "Georgia.",
        ),
    ),
)

_PRIVACY_KA = LegalDocument(
    title="Bina.ai-ის კონფიდენციალურობის პოლიტიკა",
    intro=(
        "აქ აღწერილია, რა მონაცემებს აგროვებს Bina.ai (ბოტი და მინი-აპლიკაცია "
        "ტელეგრამში), რისთვის, ვის გადასცემს და როგორ წაშალოთ ისინი."
    ),
    sections=(
        Section(
            "1. რა მონაცემებს ვინახავთ",
            "ტელეგრამიდან: თქვენი იდენტიფიკატორი, სახელი, მომხმარებლის სახელი და ენა. "
            "სერვისიდან: რჩეულები, შენახული ძებნები და შეტყობინებების პარამეტრები, "
            "Premium-ის გადახდების ისტორია (თანხა, თარიღი, გადახდის იდენტიფიკატორი), "
            "საჩივრები განცხადებებზე, ქირის შეხსენებები (თარიღი და თანხა), მეგობრების "
            "მოწვევები, კითხვები ხელოვნური ინტელექტის ასისტენტთან და ტექნიკური ჟურნალები. "
            "ტელეფონის ნომერსა და ბარათის მონაცემებს ჩვენ არ ვიღებთ.",
        ),
        Section(
            "2. რისთვის",
            "შესაფერისი განცხადებების საჩვენებლად, შეტყობინებებისა და შეხსენებების "
            "გასაგზავნად, Premium-ის ჩასართავად, მოწვევის ბონუსების დასარიცხად, "
            "თაღლითობისა და ბოროტად გამოყენების წინააღმდეგ საბრძოლველად, შეცდომების "
            "გამოსასწორებლად და სერვისის გასაუმჯობესებლად.",
        ),
        Section(
            "3. დოკუმენტები",
            "სახელები, დოკუმენტების ნომრები და სხვა მონაცემები, რომლებსაც ქირავნობის "
            "ხელშეკრულებაში ან მიღება-ჩაბარების აქტში შეიყვანთ, გამოიყენება მხოლოდ ფაილის "
            "შესაქმნელად. ფაილი გეგზავნებათ თქვენ, თავად მონაცემებს კი არ ვინახავთ.",
        ),
        Section(
            "4. ვის გადაეცემა მონაცემები",
            "ჩვენ არ ვყიდით თქვენს მონაცემებს. მათ იღებენ მხოლოდ სერვისები, რომელთა გარეშეც "
            "Bina.ai ვერ იმუშავებს: ტელეგრამი (შეტყობინებები და გადახდა), ხელოვნური "
            "ინტელექტის მოდელების მომწოდებელი (ასისტენტისთვის დასმული კითხვების ტექსტი და "
            "განცხადებების ტექსტები — თქვენი სახელისა და იდენტიფიკატორის გარეშე), "
            "Cloudflare (დაცვა და ტრაფიკის მიწოდება) და ჰოსტინგი, სადაც სერვერი მუშაობს. "
            "განცხადებების მისამართები (არა თქვენი მონაცემები) კოორდინატებად გარდაიქმნება "
            "OpenStreetMap-ის მეშვეობით. მონაცემები შეიძლება გადაეცეს სახელმწიფო ორგანოებს "
            "კანონით გათვალისწინებულ შემთხვევებში.",
        ),
        Section(
            "5. რამდენ ხანს ვინახავთ",
            "სანამ სერვისით სარგებლობთ. ბაზის სარეზერვო ასლები ინახება 14 დღემდე."
            " გადახდების მონაცემები შეიძლება უფრო დიდხანს ინახებოდეს, "
            "თუ ამას კანონი მოითხოვს.",
        ),
        Section(
            "6. თქვენი უფლებები",
            "შეგიძლიათ გაიგოთ, რა მონაცემებს ვინახავთ თქვენ შესახებ, შეასწოროთ ისინი ან "
            "მოითხოვოთ ყველაფრის წაშლა. მოგვწერეთ ბრძანებით /paysupport — ვუპასუხებთ 10 "
            "სამუშაო დღეში. ენა და შეტყობინებები შეგიძლიათ შეცვალოთ /profile-ში, რჩეულები "
            "და ძებნები კი წაშალოთ თავად სერვისში.",
        ),
        Section(
            "7. ცვლილებები",
            "შეიძლება განვაახლოთ ეს პოლიტიკა; მნიშვნელოვან ცვლილებებზე ბოტში გაცნობებთ. "
            "პოლიტიკა მოქმედებს საქართველოს პერსონალურ მონაცემთა დაცვის კანონმდებლობის "
            "შესაბამისად.",
        ),
    ),
)

DOCUMENTS: dict[LegalDoc, dict[str, LegalDocument]] = {
    LegalDoc.TERMS: {"ru": _TERMS_RU, "en": _TERMS_EN, "ka": _TERMS_KA},
    LegalDoc.PRIVACY: {"ru": _PRIVACY_RU, "en": _PRIVACY_EN, "ka": _PRIVACY_KA},
}


def legal_document(doc: LegalDoc, language: str) -> LegalDocument:
    """Документ на языке пользователя; неизвестный язык — русский."""
    texts = DOCUMENTS[doc]
    return texts.get(language, texts["ru"])


def version_label(language: str) -> str:
    """«Редакция от 30.09.2026» на языке пользователя."""
    template = VERSION_LABEL.get(language, VERSION_LABEL["ru"])
    return template.format(date=f"{VERSION:%d.%m.%Y}")
