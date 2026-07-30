// Клієнтська локалізація (UA ↔ EN) для Karro

const TRANSLATIONS = {
    'nav.login':              { uk: 'Увійти',           en: 'Sign In' },
    'nav.my_profile':         { uk: 'Мій профіль',      en: 'My Profile' },
    'nav.back':               { uk: '← Повернутись',    en: '← Go Back' },
    'nav.logout':             { uk: 'Вийти',            en: 'Log Out' },

    // Головна сторінка
    'home.badge':             { uk: 'Навчальний проєкт · ZPI-21',    en: 'Educational Project · ZPI-21' },
    'home.h1_line2':          { uk: 'твій',              en: 'your' },
    'home.h1_accent':         { uk: 'автосервіс',        en: 'auto service' },
    'home.h1_line3':          { uk: 'поруч',             en: 'nearby' },
    'home.sub':               { uk: 'Знаходь перевірені СТО, порівнюй ціни на послуги та читай відгуки реальних клієнтів.',
                                en: 'Find trusted service stations, compare prices, and read reviews from real customers.' },
    'home.btn_find':          { uk: 'Знайти СТО',        en: 'Find Station' },
    'home.btn_about':         { uk: 'Про проєкт',        en: 'About' },

    'home.about_label':       { uk: 'Про проєкт',        en: 'About' },
    'home.about_title':       { uk: 'Навіщо створено Karro?', en: 'Why was Karro created?' },
    'home.about_p1':          { uk: 'Karro — це платформа для пошуку автосервісів, розроблена як навчальний проєкт з дисципліни ZPI. Мета — дати автовласникам зручний інструмент для вибору перевіреного СТО з реальними відгуками та прозорими цінами.',
                                en: 'Karro is a platform for finding auto services, developed as an educational project for the ZPI course. The goal is to provide car owners with a convenient tool for choosing a trusted service station with real reviews and transparent pricing.' },
    'home.about_p2':          { uk: 'Власники СТО можуть реєструватись і керувати своїм профілем станції. Клієнти — шукати сервіси, прив\'язувати свої авто та залишати відгуки.',
                                en: 'Station owners can register and manage their station profile. Clients can search for services, link their cars, and leave reviews.' },

    'home.f1_title':          { uk: 'Пошук СТО',         en: 'Station Search' },
    'home.f1_desc':           { uk: 'Знаходь автосервіси за адресою, назвою або рейтингом клієнтів.',
                                en: 'Find auto services by address, name, or customer rating.' },
    'home.f2_title':          { uk: 'Відгуки та рейтинг', en: 'Reviews & Ratings' },
    'home.f2_desc':           { uk: 'Читай чесні оцінки від реальних клієнтів перед вибором сервісу.',
                                en: 'Read honest reviews from real customers before choosing a service.' },
    'home.f3_title':          { uk: 'Ціни на послуги',    en: 'Service Prices' },
    'home.f3_desc':           { uk: 'Переглядай повний прайс кожного СТО до запису.',
                                en: 'View the full price list of each station before booking.' },
    'home.f4_title':          { uk: 'Мої автомобілі',     en: 'My Cars' },
    'home.f4_desc':           { uk: 'Зберігай VIN-коди своїх авто та відстежуй сервісну історію.',
                                en: 'Save VIN codes of your cars and track service history.' },

    'home.author_label':      { uk: 'Автор',              en: 'Author' },
    'home.author_title':      { uk: 'Хто стоїть за Karro?', en: 'Who is behind Karro?' },
    'home.author_desc':       { uk: 'Проєкт розроблений студентом групи ZPI-21 від ідеї до повноцінного веб-застосунку.',
                                en: 'The project was developed by a ZPI-21 student from idea to a full-fledged web application.' },
    'home.author_bio':        { uk: 'Студент групи ZPI-21 · Проєктування бази даних, розробка серверної та клієнтської частини на Django.',
                                en: 'ZPI-21 student · Database design, Django server and client-side development.' },
    'home.footer':            { uk: '© 2026 <span>Karro</span> · Навчальний проєкт · ZPI-21 · Летінський О.',
                                en: '© 2026 <span>Karro</span> · Educational Project · ZPI-21 · Letinskyi O.' },

    // Відгуки
    'home.testimonials_label': { uk: 'Відгуки', en: 'Testimonials' },
    'home.testimonials_title': { uk: 'Що кажуть наші користувачі', en: 'What our users say' },
    'home.testimonials_sub':   { uk: 'Дивіться, що говорять про нас наші клієнти та партнери.', en: 'See what our customers and partners have to say about us.' },

    // Картки відгуків
    'home.t1_text': { uk: 'Цей сервіс повністю змінив те, як я доглядаю за своєю машиною. Завдяки цифровому гаражу я завжди бачу всю історію обслуговування, а знайти перевірене СТО поруч тепер справа кількох хвилин!', en: 'This service completely changed how I take care of my car. Thanks to the digital garage, I can always see the service history, and finding a trusted station nearby is now a matter of minutes!' },
    'home.t1_name': { uk: 'Олена Ковальчук', en: 'Olena Kovalchuk' },
    'home.t1_role': { uk: 'Власниця Audi A4', en: 'Audi A4 Owner' },

    'home.t2_text': { uk: 'Дуже зручний пошук автосервісів! Знайшов шиномонтаж біля роботи за п\'ять хвилин, ціни співпали з прайсом на сайті, а відгуки допомогли не помилитися з вибором.', en: 'Very convenient service station search! Found a tire shop near my work in five minutes, the prices matched the price list on the site, and the reviews helped me make the right choice.' },
    'home.t2_name': { uk: 'Максим Шевченко', en: 'Maksym Shevchenko' },
    'home.t2_role': { uk: 'Водій BMW X5', en: 'BMW X5 Driver' },

    'home.t3_text': { uk: 'Зареєстрував своє СТО на Karro. Кількість клієнтів помітно зросла, а вбудований кабінет допомагає зручно відстежувати доходи та керувати роботою майстрів. Рекомендую!', en: 'Registered my service station on Karro. The number of customers has grown noticeably, and the built-in cabinet helps easily track revenues and manage mechanics. Recommended!' },
    'home.t3_name': { uk: 'Дмитро Лисенко', en: 'Dmytro Lysenko' },
    'home.t3_role': { uk: 'Власник "AutoMaster"', en: 'Owner of "AutoMaster"' },

    'home.t4_text': { uk: 'Зручний інтерфейс та прозорість цін. Більше не треба обдзвонювати десятки СТО — просто ввів послугу, вибрав найкращий варіант за відгуками і записався.', en: 'Convenient interface and price transparency. No more calling dozens of stations — just enter the service, choose the best option based on reviews, and book.' },
    'home.t4_name': { uk: 'Олександр Бойко', en: 'Oleksandr Boyko' },
    'home.t4_role': { uk: 'Водій Renault Megane', en: 'Renault Megane Driver' },

    'home.t5_text': { uk: 'Завжди скептично ставився до онлайн-відгуків, але на Karro вони дійсно чесні. Вже вдруге користуюсь послугами рекомендованих автосервісів і дуже задоволений якістю.', en: 'I have always been skeptical of online reviews, but on Karro they are truly honest. This is the second time I use the recommended auto services and I am very satisfied with the quality.' },
    'home.t5_name': { uk: 'Ірина Мороз', en: 'Iryna Moroz' },
    'home.t5_role': { uk: 'Власниця Ford Fiesta', en: 'Ford Fiesta Owner' },

    'home.t6_text': { uk: 'Для власників автосервісів це чудовий інструмент. Проста реєстрація, ведення бухгалтерії та прозорий облік робіт значно полегшили менеджмент нашої станції.', en: 'For service station owners, this is an excellent tool. Simple registration, bookkeeping, and transparent work tracking have significantly simplified our station management.' },
    'home.t6_name': { uk: 'Сергій Кравченко', en: 'Serhiy Kravchenko' },
    'home.t6_role': { uk: 'Власник СТО "СТО Лівобережна"', en: 'Owner of "STO Livoberezhna"' },

    'home.t7_text': { uk: 'Мій автомобіль потребував складної комп\'ютерної діагностики. Завдяки Karro знайшов спеціалізований сервіс у Львові з відмінним рейтингом. Двигун працює ідеально!', en: 'My car required complex computer diagnostics. Thanks to Karro, I found a specialized service in Lviv with an excellent rating. The engine runs perfectly now!' },
    'home.t7_name': { uk: 'Андрій Мельник', en: 'Andriy Melnyk' },
    'home.t7_role': { uk: 'Водій Volkswagen Passat', en: 'VW Passat Driver' },

    'home.t8_text': { uk: 'Цифровий гараж із розшифровкою VIN-коду — це просто знахідка. Дуже зручно зберігати всю історію ремонту авто в одному місці та показувати її при продажу.', en: 'The digital garage with VIN code decoding is a real lifesaver. It is very convenient to store all car repair history in one place and show it when selling.' },
    'home.t8_name': { uk: 'Тетяна Петренко', en: 'Tetyana Petrenko' },
    'home.t8_role': { uk: 'Власниця Hyundai Tucson', en: 'Hyundai Tucson Owner' },

    'home.t9_text': { uk: 'Чудова служба підтримки та постійні оновлення. Karro реально спрощує життя як звичайним водіям, так і власникам бізнесу.', en: 'Excellent support team and constant updates. Karro truly simplifies life for both regular drivers and business owners.' },
    'home.t9_name': { uk: 'Ярослав Козак', en: 'Yaroslav Kozak' },
    'home.t9_role': { uk: 'Водій Skoda Octavia', en: 'Skoda Octavia Driver' },

    // Вхід та реєстрація
    'login.tab_login':        { uk: 'Вхід',               en: 'Login' },
    'login.tab_register':     { uk: 'Реєстрація',         en: 'Register' },
    'login.welcome':          { uk: 'З поверненням!',      en: 'Welcome back!' },
    'login.welcome_sub':      { uk: 'Введи свої дані для входу в Karro', en: 'Enter your credentials to sign in to Karro' },
    'login.label_email':      { uk: 'Email',              en: 'Email' },
    'login.label_password':   { uk: 'Пароль',             en: 'Password' },
    'login.btn_login':        { uk: 'Увійти →',           en: 'Sign In →' },
    'login.or':               { uk: 'або',                en: 'or' },
    'login.no_account':       { uk: 'Немає акаунту?',      en: "Don't have an account?" },
    'login.link_register':    { uk: 'Зареєструватись',     en: 'Sign Up' },

    'reg.title':              { uk: 'Створи акаунт',       en: 'Create Account' },
    'reg.subtitle':           { uk: 'Приєднуйся до Karro безкоштовно', en: 'Join Karro for free' },
    'reg.label_name':         { uk: "Повне ім'я",          en: 'Full Name' },
    'reg.label_phone':        { uk: 'Телефон',             en: 'Phone' },
    'reg.label_email':        { uk: 'Email',               en: 'Email' },
    'reg.label_password':     { uk: 'Пароль',              en: 'Password' },
    'reg.label_password2':    { uk: 'Повторити',           en: 'Confirm' },
    'reg.label_role':         { uk: 'Я є...',              en: 'I am...' },
    'reg.role_client':        { uk: 'Клієнт',              en: 'Client' },
    'reg.role_station':       { uk: 'Власник СТО',         en: 'Station Owner' },
    'reg.btn_register':       { uk: 'Зареєструватись →',   en: 'Sign Up →' },
    'reg.has_account':        { uk: 'Вже є акаунт?',       en: 'Already have an account?' },
    'reg.link_login':         { uk: 'Увійти',              en: 'Sign In' },
    'login.footer':           { uk: '© 2026 <a href="/">Karro</a> · ZPI-21 · Летінський О.',
                                en: '© 2026 <a href="/">Karro</a> · ZPI-21 · Letinskyi O.' },

    'ph.email':               { uk: 'you@example.com',     en: 'you@example.com' },
    'ph.password':            { uk: '••••••••',            en: '••••••••' },
    'ph.full_name':           { uk: 'Іван Петренко',       en: 'John Doe' },
    'ph.phone':               { uk: '+380671234567',       en: '+380671234567' },

    // Особистий кабінет
    'profile.role_client':    { uk: 'Клієнт',              en: 'Client' },
    'profile.role_station':   { uk: 'Власник СТО',         en: 'Station Owner' },

    'profile.nav_info':       { uk: 'Особисті дані',       en: 'Personal Info' },
    'profile.nav_cars':       { uk: 'Мої автомобілі',      en: 'My Cars' },
    'profile.nav_reviews':    { uk: 'Мої відгуки',         en: 'My Reviews' },
    'profile.nav_station':    { uk: 'Моя СТО',             en: 'My Station' },
    'profile.nav_services':   { uk: 'Послуги',             en: 'Services' },
    'profile.nav_settings':   { uk: 'Налаштування',        en: 'Settings' },

    'profile.info_title':     { uk: 'Особисті дані',       en: 'Personal Info' },
    'profile.info_sub':       { uk: "Оновлюй своє ім'я та контакти", en: 'Update your name and contacts' },
    'profile.label_name':     { uk: "Повне ім'я",          en: 'Full Name' },
    'profile.label_phone':    { uk: 'Телефон',             en: 'Phone' },
    'profile.label_email':    { uk: 'Email',               en: 'Email' },
    'profile.btn_save':       { uk: 'Зберегти зміни',      en: 'Save Changes' },

    'profile.settings_title': { uk: 'Налаштування',        en: 'Settings' },
    'profile.settings_sub':   { uk: 'Мова та параметри інтерфейсу', en: 'Language and interface preferences' },
    'profile.label_lang':     { uk: 'Мова інтерфейсу',     en: 'Interface Language' },

    'profile.pwd_title':      { uk: 'Зміна пароля',        en: 'Change Password' },
    'profile.pwd_sub':        { uk: 'Встанови новий пароль для входу', en: 'Set a new password for login' },
    'profile.label_new_pwd':  { uk: 'Новий пароль',        en: 'New Password' },
    'profile.label_new_pwd2': { uk: 'Повторити пароль',    en: 'Confirm Password' },
    'profile.btn_change_pwd': { uk: 'Змінити пароль',      en: 'Change Password' },

    'profile.cars_title':     { uk: 'Мої автомобілі',      en: 'My Cars' },
    'profile.cars_sub':       { uk: "Автомобілі прив'язані до твого акаунту", en: 'Cars linked to your account' },
    'profile.no_cars':        { uk: 'Ще немає доданих автомобілів', en: 'No cars added yet' },
    'profile.add_car_title':  { uk: 'Додати автомобіль',   en: 'Add Car' },
    'profile.add_car_sub':    { uk: 'Введи дані свого авто', en: 'Enter your car details' },
    'profile.label_vin':      { uk: 'VIN-код',             en: 'VIN Code' },
    'profile.label_brand':    { uk: 'Марка',               en: 'Brand' },
    'profile.label_model':    { uk: 'Модель',              en: 'Model' },
    'profile.label_year':     { uk: 'Рік випуску',         en: 'Year' },
    'profile.btn_add_car':    { uk: 'Додати авто',         en: 'Add Car' },
    'profile.btn_delete':     { uk: 'Видалити',            en: 'Delete' },
    'profile.change_photo':   { uk: 'Змінити фото',        en: 'Change Photo' },
    'profile.add_photo':      { uk: 'Додати фото авто',    en: 'Add Car Photo' },

    'profile.reviews_title':  { uk: 'Мої відгуки',         en: 'My Reviews' },
    'profile.reviews_sub':    { uk: 'Відгуки які ти залишив на СТО', en: 'Reviews you left for stations' },
    'profile.no_reviews':     { uk: 'Ти ще не залишав відгуків', en: "You haven't left any reviews yet" },

    'profile.station_title':  { uk: 'Профіль СТО',         en: 'Station Profile' },
    'profile.station_sub':    { uk: 'Дані твоєї станції технічного обслуговування', en: 'Your service station details' },
    'profile.label_st_name':  { uk: 'Назва СТО',           en: 'Station Name' },
    'profile.label_st_addr':  { uk: 'Адреса',              en: 'Address' },
    'profile.label_st_phone': { uk: 'Телефон СТО',         en: 'Station Phone' },
    'profile.btn_update_st':  { uk: 'Оновити дані',        en: 'Update Info' },
    'profile.btn_create_st':  { uk: 'Створити СТО',        en: 'Create Station' },

    'profile.svc_title':      { uk: 'Послуги СТО',         en: 'Station Services' },
    'profile.svc_sub':        { uk: 'Керуй переліком послуг твоєї станції', en: 'Manage the service list of your station' },
    'profile.no_services':    { uk: 'Послуг ще немає. Додай першу!', en: 'No services yet. Add the first one!' },
    'profile.add_svc_title':  { uk: 'Додати послугу',      en: 'Add Service' },
    'profile.label_svc_name': { uk: 'Назва послуги',       en: 'Service Name' },
    'profile.label_svc_price':{ uk: 'Ціна (грн)',          en: 'Price (UAH)' },
    'profile.label_svc_desc': { uk: "Опис (необов'язково)", en: 'Description (optional)' },
    'profile.btn_add_svc':    { uk: 'Додати послугу',      en: 'Add Service' },

    'ph.station_name':        { uk: 'AutoMaster',          en: 'AutoMaster' },
    'ph.station_addr':        { uk: 'вул. Гагаріна 15, Київ', en: '15 Gagarin St, Kyiv' },
    'ph.station_phone':       { uk: '+380441234567',       en: '+380441234567' },
    'ph.svc_name':            { uk: 'Заміна масла',        en: 'Oil Change' },
    'ph.svc_desc':            { uk: 'Короткий опис послуги...', en: 'Brief description of the service...' },

    // Пошук
    'search.label_city':      { uk: 'Місто',               en: 'City' },
    'search.label_service':   { uk: 'Послуга',             en: 'Service' },
    'search.label_rating':    { uk: 'Мін. рейтинг',        en: 'Min. Rating' },
    'search.rating_any':      { uk: 'Будь-який',           en: 'Any' },
    'search.btn_find':        { uk: 'Знайти',              en: 'Search' },
    'search.btn_reset':       { uk: '✕ Скинути',           en: '✕ Reset' },
    'search.no_reviews':      { uk: 'Без відгуків',        en: 'No reviews' },
    'search.btn_detail':      { uk: 'Детальніше →',        en: 'Details →' },
    'search.empty':           { uk: 'Нічого не знайдено.<br>Спробуй змінити фільтри.',
                                en: 'Nothing found.<br>Try changing the filters.' },
    'search.results_found':   { uk: 'Знайдено:',          en: 'Found:' },
    'search.results_sto':     { uk: 'СТО',                en: 'stations' },
    'search.results_city':    { uk: 'місто:',              en: 'city:' },
    'search.results_service': { uk: 'послуга:',            en: 'service:' },

    'ph.city':                { uk: 'Київ, Львів…',        en: 'Kyiv, Lviv…' },
    'ph.service':             { uk: 'Заміна масла…',       en: 'Oil change…' },

    // Повідомлення
    'msg.address_en_only':    { uk: 'Адреса повинна бути тільки англійською мовою.', en: 'Address must be in English only.' },

    // Бухгалтерія (Accounting)
    'profile.nav_accounting':   { uk: 'Бухгалтерія',      en: 'Accounting' },
    'acc.title':                { uk: 'Бухгалтерія та персонал', en: 'Accounting & Staff' },
    'acc.subtitle':             { uk: 'Управління фінансами, працівниками та зарплатами', en: 'Manage finances, employees, and salaries' },
    'acc.metric_income':        { uk: 'Загальний дохід',   en: 'Total Revenue' },
    'acc.metric_expense':       { uk: 'Витрати',          en: 'Expenses' },
    'acc.metric_profit':        { uk: 'Чистий прибуток',   en: 'Net Profit' },
    'acc.metric_salaries':      { uk: 'Борг по зарплатах',  en: 'Salaries Owed' },
    'acc.analytic_title':       { uk: 'Розподіл витрат за категоріями', en: 'Expense Distribution by Category' },
    'acc.no_expenses':          { uk: 'Немає витрат за вказаний період', en: 'No expenses for this period' },
    'acc.staff_title':          { uk: 'Штат працівників',   en: 'Staff & Employees' },
    'acc.btn_add_employee':     { uk: 'Додати працівника',  en: 'Add Employee' },
    'acc.tbl_name':             { uk: "Ім'я",             en: 'Name' },
    'acc.tbl_position':         { uk: 'Посада',           en: 'Position' },
    'acc.tbl_rate':             { uk: 'Ставка / %',       en: 'Rate / %' },
    'acc.tbl_balance':          { uk: 'До виплати',        en: 'To Pay' },
    'acc.tbl_actions':          { uk: 'Дії',              en: 'Actions' },
    'acc.btn_pay':              { uk: 'Виплатити',        en: 'Pay Out' },
    'acc.fired':                { uk: 'Звільнений',        en: 'Fired' },
    'acc.btn_reactivate':       { uk: 'Поновити',          en: 'Reactivate' },
    'acc.no_staff':             { uk: 'Штат порожній. Додайте першого працівника!', en: 'No staff registered. Add the first employee!' },
    'acc.transactions_title':   { uk: 'Журнал операцій',   en: 'Transactions Log' },
    'acc.btn_add_transaction':  { uk: 'Нова операція',     en: 'New Transaction' },
    'acc.tbl_date':             { uk: 'Дата',             en: 'Date' },
    'acc.tbl_desc':             { uk: 'Опис',             en: 'Description' },
    'acc.tbl_amount':           { uk: 'Сума',             en: 'Amount' },
    'acc.no_transactions':      { uk: 'Немає транзакцій за обраний період.', en: 'No transactions logged for this period.' },
    'acc.add_emp_title':        { uk: 'Додати нового працівника', en: 'Add New Employee' },
    'acc.lbl_emp_name':         { uk: "Повне ім'я *",     en: 'Full Name *' },
    'acc.lbl_emp_phone':        { uk: 'Телефон',          en: 'Phone' },
    'acc.lbl_emp_pos':          { uk: 'Посада *',         en: 'Position *' },
    'acc.lbl_emp_rate':         { uk: 'Денна/Місячна ставка (грн) *', en: 'Base Salary (UAH) *' },
    'acc.lbl_emp_comm':         { uk: 'Комісія від замовлень (%) *', en: 'Job Commission (%) *' },
    'acc.edit_emp_title':       { uk: 'Редагувати дані працівника', en: 'Edit Employee Details' },
    'acc.chk_active':           { uk: 'Активний працівник (поновити на роботі)', en: 'Active employee (reactivate)' },
    'acc.pay_salary_title':     { uk: 'Виплатити зарплату', en: 'Pay Employee Salary' },
    'acc.lbl_payout_target':    { uk: 'Працівник:',        en: 'Employee:' },
    'acc.lbl_payout_amount':    { uk: 'Сума виплати (грн) *', en: 'Payout Amount (UAH) *' },
    'acc.max_avail':            { uk: 'Максимум доступно:', en: 'Max available:' },
    'acc.btn_confirm_payout':   { uk: 'Підтвердити виплату', en: 'Confirm Payout' },
    'acc.new_tx_title':         { uk: 'Внести нову фінансову операцію', en: 'Record Financial Transaction' },
    'acc.lbl_tx_type':          { uk: 'Тип операції *',    en: 'Transaction Type *' },
    'acc.opt_expense':          { uk: 'Витрата',          en: 'Expense' },
    'acc.opt_income':           { uk: 'Дохід',            en: 'Income' },
    'acc.lbl_tx_category':      { uk: 'Категорія *',       en: 'Category *' },
    'acc.cat_spare_parts':      { uk: 'Запчастини',        en: 'Spare Parts' },
    'acc.cat_rent':             { uk: 'Оренда',           en: 'Rent' },
    'acc.cat_utilities':        { uk: 'Комунальні послуги', en: 'Utilities' },
    'acc.cat_other_expense':    { uk: 'Інші витрати',      en: 'Other Expense' },
    'acc.cat_service':          { uk: 'Послуги СТО (Ремонт)', en: 'Service Revenue' },
    'acc.cat_other_income':     { uk: 'Інші доходи',       en: 'Other Income' },
    'acc.lbl_tx_amount':        { uk: 'Сума (грн) *',     en: 'Amount (UAH) *' },
    'acc.lbl_tx_date':          { uk: 'Дата *',           en: 'Date *' },
    'acc.lbl_tx_desc':          { uk: 'Опис / Примітка',   en: 'Description / Note' },
    'acc.complete_title':       { uk: 'Завершення ремонту', en: 'Complete Repair' },
    'acc.lbl_actual_price':     { uk: 'Вартість виконаних робіт (грн) *', en: 'Actual Work Price (UAH) *' },
    'acc.lbl_assigned_emp':     { uk: 'Виконавець (Співробітник)', en: 'Assigned Mechanic' },
    'acc.opt_no_emp':           { uk: '-- Без виконавця (без комісії) --', en: '-- No mechanic (no commission) --' },
    'acc.comm_notice':          { uk: 'Обраному співробітнику буде нараховано його відсоток комісії.', en: 'Selected employee will automatically earn their commission.' },
    'acc.btn_complete_repair':  { uk: 'Завершити ремонт',  en: 'Complete Repair & Log Revenue' },
    'acc.btn_save':             { uk: 'Зберегти',         en: 'Save' },
    
    // Сповіщення / Notifications
    'notifications.title':           { uk: 'Сповіщення',       en: 'Notifications' },
    'notifications.mark_all_read':   { uk: 'Позначити все як прочитане', en: 'Mark all as read' },
    'notifications.empty':           { uk: 'Немає нових сповіщень', en: 'No new notifications' },
};

// Робота з мовою інтерфейсу
function getLang() {
    return localStorage.getItem('karro_lang') || 'uk';
}

function setLang(lang) {
    localStorage.setItem('karro_lang', lang);
    applyTranslations(lang);
    updateToggleButton(lang);
    document.documentElement.lang = lang;
}

function applyTranslations(lang) {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (TRANSLATIONS[key] && TRANSLATIONS[key][lang] !== undefined) {
            el.textContent = TRANSLATIONS[key][lang];
        }
    });

    document.querySelectorAll('[data-i18n-html]').forEach(el => {
        const key = el.getAttribute('data-i18n-html');
        if (TRANSLATIONS[key] && TRANSLATIONS[key][lang] !== undefined) {
            el.innerHTML = TRANSLATIONS[key][lang];
        }
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (TRANSLATIONS[key] && TRANSLATIONS[key][lang] !== undefined) {
            el.placeholder = TRANSLATIONS[key][lang];
        }
    });

    const titleEl = document.querySelector('[data-i18n-title]');
    if (titleEl) {
        const key = titleEl.getAttribute('data-i18n-title');
        if (TRANSLATIONS[key] && TRANSLATIONS[key][lang] !== undefined) {
            document.title = TRANSLATIONS[key][lang];
        }
    }

    document.querySelectorAll('.alert').forEach(el => {
        const text = el.textContent.trim();
        for (const [key, val] of Object.entries(TRANSLATIONS)) {
            if (val.uk === text || val.en === text) {
                el.textContent = val[lang];
                break;
            }
        }
    });
}

function initLangSelect() {
    const select = document.getElementById('lang-select');
    if (!select) return;

    const currentLang = getLang();
    select.value = currentLang;

    select.addEventListener('change', (e) => {
        setLang(e.target.value);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const lang = getLang();
    if (lang !== 'uk') {
        applyTranslations(lang);
    }
    document.documentElement.lang = lang;
    initLangSelect();
});
