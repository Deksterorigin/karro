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
    'home.author_bio':        { uk: 'Студент групи ZPI-21 · Проєктування бази даних, розробка серверної та клієнтської частини на Django.',
                                en: 'ZPI-21 student · Database design, Django server and client-side development.' },
    'home.footer':            { uk: '© 2026 <span>Karro</span> · Навчальний проєкт · ZPI-21 · Летінський О.',
                                en: '© 2026 <span>Karro</span> · Educational Project · ZPI-21 · Letinskyi O.' },

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
    'search.btn_reset':       { uk: 'Скинути',             en: 'Reset' },
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
    'acc.title':                { uk: 'Бухгалтерія та Кадри', en: 'Accounting & HR' },
    'acc.subtitle':             { uk: 'Аналітика доходів, витрат та управління персоналом СТО', en: 'Revenue and expense analytics plus staff management' },
    'acc.metric_income':        { uk: 'Загальний дохід',   en: 'Total Revenue' },
    'acc.metric_expense':       { uk: 'Витрати СТО',      en: 'Station Expenses' },
    'acc.metric_profit':        { uk: 'Чистий прибуток',   en: 'Net Profit' },
    'acc.metric_salaries':      { uk: 'Невиплачена зарплата', en: 'Unpaid Salaries' },
    'acc.analytic_title':       { uk: 'Структура витрат за категоріями', en: 'Expense Breakdown by Category' },
    'acc.trend_title':          { uk: 'Динаміка доходів та витрат', en: 'Income & Expense Dynamics' },
    'acc.no_expenses':          { uk: 'Немає витрат за обраний період для побудови структури', en: 'No expenses for this period yet' },
    'acc.staff_title':          { uk: 'Штат працівників',   en: 'Staff & Employees' },
    'acc.btn_add_employee':     { uk: 'Додати працівника',  en: 'Add Employee' },
    'acc.tbl_name':             { uk: "Ім'я",             en: 'Name' },
    'acc.tbl_position':         { uk: 'Посада',           en: 'Position' },
    'acc.tbl_rate':             { uk: 'Ставка / Відсоток', en: 'Rate / %' },
    'acc.tbl_balance':          { uk: 'Баланс до виплати', en: 'Balance Due' },
    'acc.tbl_actions':          { uk: 'Дії',              en: 'Actions' },
    'acc.btn_pay':              { uk: 'Виплатити',        en: 'Pay Out' },
    'acc.fired':                { uk: 'Звільнений',        en: 'Fired' },
    'acc.btn_reactivate':       { uk: 'Поновити',          en: 'Reactivate' },
    'acc.no_staff':             { uk: 'Штат порожній. Будь ласка, додайте першого співробітника!', en: 'No staff yet. Please add the first employee!' },
    'acc.transactions_title':   { uk: 'Журнал операцій',   en: 'Transactions Log' },
    'acc.btn_add_transaction':  { uk: 'Нова транзакція',   en: 'New Transaction' },
    'acc.tbl_date':             { uk: 'Дата',             en: 'Date' },
    'acc.tbl_desc':             { uk: 'Опис операції',    en: 'Description' },
    'acc.tbl_amount':           { uk: 'Сума (грн)',       en: 'Amount (UAH)' },
    'acc.no_transactions':      { uk: 'Немає транзакцій, які відповідають обраним критеріям фільтрації.', en: 'No transactions match the selected filters.' },
    'acc.add_emp_title':        { uk: 'Додати нового працівника', en: 'Add New Employee' },
    'acc.lbl_emp_name':         { uk: "Повне ім'я *",     en: 'Full Name *' },
    'acc.lbl_emp_phone':        { uk: 'Телефон',          en: 'Phone' },
    'acc.lbl_emp_pos':          { uk: 'Посада *',         en: 'Position *' },
    'acc.lbl_emp_rate':         { uk: 'Ставка (грн/міс або грн/день) *', en: 'Rate (UAH/month or UAH/day) *' },
    'acc.lbl_emp_comm':         { uk: 'Комісія від замовлень (%) *', en: 'Job Commission (%) *' },
    'acc.edit_emp_title':       { uk: 'Редагувати дані працівника', en: 'Edit Employee Details' },
    'acc.chk_active':           { uk: 'Активний працівник (поновити на роботі)', en: 'Active employee (reactivate)' },
    'acc.pay_salary_title':     { uk: 'Виплатити заробітну плату', en: 'Pay Salary' },
    'acc.lbl_payout_target':    { uk: 'Працівник:',        en: 'Employee:' },
    'acc.lbl_payout_amount':    { uk: 'Сума виплати (грн) *', en: 'Payout Amount (UAH) *' },
    'acc.max_avail':            { uk: 'Доступний баланс:', en: 'Available balance:' },
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
    'acc.lbl_tx_date':          { uk: 'Дата операції *',  en: 'Transaction Date *' },
    'acc.lbl_tx_desc':          { uk: 'Опис / Коментар до транзакції', en: 'Description / Comment' },
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
    // --- Заголовки вкладок браузера ---
    'home.title':             { uk: 'Karro — Знайди свій автосервіс', en: 'Karro — Find Your Auto Service' },
    'login.title':            { uk: 'Karro — Вхід / Реєстрація', en: 'Karro — Sign In / Register' },
    'profile.title':          { uk: 'Karro — Профіль',  en: 'Karro — Profile' },
    'search.title':           { uk: 'Пошук СТО — Karro', en: 'Find a Station — Karro' },
    'acc.page_title':         { uk: 'Karro — Бухгалтерія та персонал', en: 'Karro — Accounting & Staff' },
    'client.title':           { uk: 'Профіль клієнта',  en: 'Client Profile' },

    // --- Доступність ---
    'aria.open_menu':         { uk: 'Відкрити меню',    en: 'Open menu' },
    'aria.toggle_theme':      { uk: 'Переключити тему', en: 'Toggle theme' },

    // --- Загальні слова ---
    'common.not_specified':   { uk: 'Не вказано',       en: 'Not specified' },
    'common.delete':          { uk: 'Видалити',         en: 'Delete' },
    'common.edit':            { uk: 'Редагувати',       en: 'Edit' },
    'common.active':          { uk: 'Активний',         en: 'Active' },
    'common.inactive':        { uk: 'Неактивний',       en: 'Inactive' },
    'common.sto':             { uk: 'СТО:',             en: 'Station:' },
    'common.date_word':       { uk: 'Дата:',            en: 'Date:' },
    'common.year_word':       { uk: 'Рік випуску:',     en: 'Year:' },
    'common.km':              { uk: 'км',               en: 'km' },
    'common.uah':             { uk: 'грн',              en: 'UAH' },
    'common.to':              { uk: 'до',               en: 'to' },
    'common.client':          { uk: 'Клієнт',           en: 'Client' },
    'common.car':             { uk: 'Автомобіль',       en: 'Car' },
    'common.connection_error':{ uk: "Помилка з'єднання із сервером", en: 'Server connection error' },
    'common.price_caption':   { uk: 'Вартість робіт',   en: 'Service price' },

    // --- Кабінет клієнта (сторінка клієнта) ---
    'client.back_to_bookings':{ uk: 'Назад до заявок',  en: 'Back to bookings' },
    'client.cars_title':      { uk: 'Автомобілі клієнта', en: "Client's Cars" },
    'client.no_cars':         { uk: 'Цей клієнт ще не додав жодного автомобіля.', en: 'This client has not added any cars yet.' },

    // --- Пошук: нове ---
    'search.label_radius':    { uk: 'Радіус',           en: 'Radius' },
    'search.radius_all':      { uk: 'Усі',              en: 'All' },
    'search.btn_nearby':      { uk: 'Поруч',            en: 'Nearby' },
    'search.tab_list':        { uk: 'Список',           en: 'List' },
    'search.tab_map':         { uk: 'Карта',            en: 'Map' },
    'search.distance':        { uk: 'Відстань:',        en: 'Distance:' },
    'search.geo_unsupported': { uk: 'Ваш браузер не підтримує геолокацію.', en: 'Your browser does not support geolocation.' },
    'search.locating':        { uk: 'Визначення...',    en: 'Locating...' },
    'search.geo_denied_short':{ uk: 'Неможливо отримати геолокацію.', en: 'Unable to get your location.' },
    'search.geo_denied':      { uk: 'Будь ласка, дозвольте доступ до геопозиції у налаштуваннях браузера.', en: 'Please allow location access in your browser settings.' },
    'search.you_are_here':    { uk: 'Ви знаходитесь тут', en: 'You are here' },
    'search.popup_details':   { uk: 'Переглянути СТО',  en: 'View station' },

    // --- Головна сторінка: нове ---
    'home.popular_label':     { uk: 'Популярне:',       en: 'Popular:' },
    'home.tag_tires':         { uk: 'Шиномонтаж',       en: 'Tire Service' },
    'home.tag_diagnostics':   { uk: 'Діагностика',      en: 'Diagnostics' },
    'home.tag_maintenance':   { uk: 'Планове ТО',       en: 'Scheduled Maintenance' },
    'home.about_sub':         { uk: 'Простий та прозорий шлях від пошуку несправності до якісного обслуговування авто',
                                en: 'A simple and clear path from troubleshooting to quality car care' },
    'home.rec_title':         { uk: 'Популярні напрямки обслуговування', en: 'Popular Service Categories' },
    'home.all_stations_link': { uk: 'Всі автосервіси',  en: 'All Auto Services' },
    'home.cat1_desc':         { uk: "Повний спектр догляду за екстер'єром та інтер'єром автомобіля, полірування та захист.",
                                en: 'Full-range exterior and interior care, polishing and protection.' },
    'home.cat2_desc':         { uk: "Комп'ютерна діагностика систем, аналіз помилок, ремонт двигунів та паливних систем.",
                                en: 'Computer diagnostics, error analysis, engine and fuel system repair.' },
    'home.cat3_desc':         { uk: 'Швидкий шиномонтаж, балансування коліс, діагностика підвіски та заміна амортизаторів.',
                                en: 'Fast tire fitting, wheel balancing, suspension diagnostics and shock absorber replacement.' },
    'home.cat1_price':        { uk: 'від 300 грн',      en: 'from 300 UAH' },
    'home.cat2_price':        { uk: 'від 250 грн',      en: 'from 250 UAH' },
    'home.cat3_price':        { uk: 'від 180 грн',      en: 'from 180 UAH' },
    'home.find_kyiv':         { uk: 'Знайти в Києві',   en: 'Find in Kyiv' },
    'home.find_lviv':         { uk: 'Знайти у Львові',  en: 'Find in Lviv' },
    'home.find_odesa':        { uk: 'Знайти в Одесі',   en: 'Find in Odesa' },
    'home.garage_title':      { uk: 'Твій Цифровий Гараж', en: 'Your Digital Garage' },
    'home.garage_desc':       { uk: 'Зберігай інформацію про свої автомобілі у особистому кабінеті. Достатньо ввести 17-значний VIN-код, щоб автоматично розшифрувати марку, модель та рік випуску вашого транспортного засобу та вести його єдину сервісну історію.',
                                en: 'Store your cars in your personal dashboard. Just enter the 17-character VIN code to automatically decode the make, model and year, and keep a single service history.' },
    'home.gf1_title':         { uk: 'Автоматичне декодування VIN', en: 'Automatic VIN decoding' },
    'home.gf1_text':          { uk: 'Розпізнавання марки, моделі, типу двигуна та року випуску', en: 'Recognizes make, model, engine type and year' },
    'home.gf2_title':         { uk: 'Єдиний сервісний паспорт', en: 'Single service passport' },
    'home.gf2_text':          { uk: 'Всі акти виконаних робіт, пробіг та чеки в одному надійному місці', en: 'All work acts, mileage and receipts in one reliable place' },
    'home.gf3_title':         { uk: 'Погодження кошторису робіт', en: 'Cost estimate approval' },
    'home.gf3_text':          { uk: 'Підтверджуйте або відхиляйте додаткові роботи майстра у вбудованому чаті', en: 'Approve or decline extra works from the mechanic in the built-in chat' },
    'home.btn_cabinet':       { uk: 'Увійти в кабінет', en: 'Open Dashboard' },
    'home.btn_try_garage':    { uk: 'Спробувати Гараж', en: 'Try the Garage' },
    'home.phone_garage':      { uk: 'Мій Гараж',        en: 'My Garage' },
    'home.timeline_title':    { uk: 'Історія обслуговування', en: 'Service History' },
    'home.records_3':         { uk: '3 записи',         en: '3 records' },
    'home.tl1_title':         { uk: 'Заміна мастила та фільтрів', en: 'Oil & filter change' },
    'home.tl2_title':         { uk: 'Діагностика підвіски', en: 'Suspension diagnostics' },
    'home.biz_title':         { uk: 'Маєте СТО? Зареєструйте її на Karro', en: 'Own a station? List it on Karro' },
    'home.biz_desc':          { uk: 'Отримайте потік нових клієнтів у вашому місті. Зареєструйте кабінет СТО, публікуйте прайс-лист, відповідайте на відгуки клієнтів та ведіть календар записів і фінансовий облік станції.',
                                en: 'Get a flow of new clients in your city. Register a station dashboard, publish your price list, reply to reviews and manage bookings and finances.' },

    // --- Сторінка СТО ---
    'st.back_to_search':      { uk: 'Назад до пошуку',  en: 'Back to search' },
    'st.reviews_word':        { uk: 'відгуки',          en: 'reviews' },
    'st.based_on':            { uk: 'на основі',        en: 'based on' },
    'st.owner_badge':         { uk: 'Ви — власник цієї СТО', en: 'You own this station' },
    'st.book_repair':         { uk: 'Записатися на ремонт', en: 'Book a Repair' },
    'st.services_title':      { uk: 'Послуги',          en: 'Services' },
    'st.no_services':         { uk: 'Послуги ще не додані', en: 'No services added yet' },
    'st.gallery_title':       { uk: 'Фотогалерея',      en: 'Photo Gallery' },
    'st.no_photos':           { uk: 'Фотографій ще немає', en: 'No photos yet' },
    'st.upload_hint':         { uk: 'Натисніть для завантаження фото', en: 'Click to upload a photo' },
    'st.btn_upload':          { uk: 'Завантажити',      en: 'Upload' },
    'st.reviews_title':       { uk: 'Відгуки',          en: 'Reviews' },
    'st.owner_response':      { uk: 'Відповідь автосервісу', en: "Station's Reply" },
    'st.reply_review':        { uk: 'Відповісти на відгук', en: 'Reply to review' },
    'st.publish_reply':       { uk: 'Опублікувати відповідь', en: 'Publish reply' },
    'st.no_reviews':          { uk: 'Відгуків ще немає. Будьте першим!', en: 'No reviews yet. Be the first!' },
    'st.leave_review':        { uk: 'Залишити відгук',  en: 'Leave a Review' },
    'st.attach_photo':        { uk: "Прикріпити фото до відгуку (необов'язково):", en: 'Attach a photo (optional):' },
    'st.submit_review':       { uk: 'Надіслати відгук', en: 'Submit Review' },
    'st.login_to_review':     { uk: 'Щоб залишити відгук, увійдіть в акаунт', en: 'Sign in to leave a review' },
    'st.contacts':            { uk: 'Контакти',         en: 'Contacts' },
    'st.owner_label':         { uk: 'Власник',          en: 'Owner' },
    'st.schedule':            { uk: 'Графік роботи',    en: 'Working Hours' },
    'st.open_now':            { uk: 'Зараз відчинено',  en: 'Open now' },
    'st.closed_now':          { uk: 'Зараз зачинено',   en: 'Closed now' },
    'st.day_off':             { uk: 'Вихідний',         en: 'Day off' },
    'st.break_word':          { uk: 'обід',             en: 'break' },
    'st.on_map':              { uk: 'На карті',         en: 'On the map' },
    'st.delete_photo':        { uk: 'Видалити фото',    en: 'Delete photo' },
    'st.booking_title':       { uk: 'Запис на ремонт',  en: 'Book a Repair' },
    'st.label_car':           { uk: 'Оберіть автомобіль', en: 'Choose a car' },
    'st.choose_car':          { uk: 'Оберіть автомобіль з вашого гаражу', en: 'Choose a car from your garage' },
    'st.no_cars_html':        { uk: 'У вас немає доданих автомобілів. Будь ласка, <a href="/profile/" style="color: var(--accent); text-decoration: underline;">додайте авто в гараж</a> перед записом.',
                                en: 'You have no cars added. Please <a href="/profile/" style="color: var(--accent); text-decoration: underline;">add a car to your garage</a> before booking.' },
    'st.no_cars_option':      { uk: 'Немає доступних автомобілів', en: 'No cars available' },
    'st.login_as_client':     { uk: 'Будь ласка, увійдіть як клієнт', en: 'Please sign in as a client' },
    'st.label_problem':       { uk: 'Опис проблеми',    en: 'Problem Description' },
    'st.label_duration':      { uk: 'Очікувана тривалість ремонту', en: 'Expected repair duration' },
    'st.dur_30':              { uk: '30 хвилин',        en: '30 minutes' },
    'st.dur_60':              { uk: '1 година',         en: '1 hour' },
    'st.dur_120':             { uk: '2 години',         en: '2 hours' },
    'st.dur_180':             { uk: '3 години',         en: '3 hours' },
    'st.dur_240':             { uk: '4 години',         en: '4 hours' },
    'st.label_date':          { uk: 'Оберіть дату візиту', en: 'Choose a visit date' },
    'st.label_time':          { uk: 'Доступний час візиту', en: 'Available time slots' },
    'st.hours_prefix':        { uk: 'Робочі години: з', en: 'Working hours: from' },
    'st.pick_date_hint':      { uk: 'Будь ласка, оберіть дату для пошуку вільних слотів.', en: 'Please pick a date to see available slots.' },
    'st.submit_booking':      { uk: 'Відправити заявку', en: 'Submit Booking' },
    'st.loading_slots':       { uk: 'Завантаження слотів...', en: 'Loading slots...' },
    'st.closed_day_msg':      { uk: 'СТО не працює у цей день (Вихідний).', en: 'The station is closed on this day.' },
    'st.no_slots_left':       { uk: 'Немає вільних боксів на цю дату. Оберіть інший день або час.', en: 'No free slots left for this date. Try another day or time.' },
    'st.slots_error':         { uk: 'Помилка завантаження слотів', en: 'Failed to load slots' },
    'st.pick_slot_alert':     { uk: 'Будь ласка, оберіть час візиту зі списку вільних слотів.', en: 'Please pick a time from the available slots.' },
    'st.fill_all_fields':     { uk: 'Будь ласка, заповніть всі поля перед відправкою.', en: 'Please fill in all fields before submitting.' },
    'st.server_error':        { uk: 'Помилка сервера',  en: 'Server error' },
    'st.login_required':      { uk: 'Будь ласка, авторизуйтесь для запису на СТО.', en: 'Please sign in to book a station.' },

    // --- Профіль: навігація та нове ---
    'profile.nav_my_bookings':{ uk: 'Мої записи',       en: 'My Visits' },
    'profile.nav_bookings':   { uk: 'Заявки',           en: 'Bookings' },
    'profile.nav_calendar':   { uk: 'Календар',         en: 'Calendar' },
    'profile.nav_inventory':  { uk: 'Склад запчастин',  en: 'Parts Inventory' },
    'profile.nav_schedule':   { uk: 'Графік роботи',    en: 'Working Hours' },
    'profile.label_old_pwd':  { uk: 'Поточний пароль',  en: 'Current Password' },
    'profile.history_toggle': { uk: 'Історія обслуговування', en: 'Service History' },
    'profile.mileage_word':   { uk: 'Пробіг:',          en: 'Mileage:' },
    'profile.works_done':     { uk: 'Виконані роботи:', en: 'Work performed:' },
    'profile.parts_used':     { uk: 'Використані запчастини:', en: 'Spare parts used:' },
    'profile.history_empty':  { uk: 'Історія обслуговування порожня.', en: 'No service history yet.' },
    'profile.garage_title':   { uk: 'Цифровий Гараж',   en: 'Digital Garage' },
    'profile.garage_sub':     { uk: 'Історія обслуговування твоїх автомобілів', en: 'Service history of your cars' },
    'profile.no_bookings_car':{ uk: 'Немає зареєстрованих ремонтів або заявок для цього автомобіля.', en: 'No repairs or bookings registered for this car.' },
    'profile.garage_empty':   { uk: 'У твоєму цифровому гаражі немає доданих авто.', en: 'Your digital garage has no cars yet.' },
    'profile.add_first_car':  { uk: 'Додати перший автомобіль', en: 'Add Your First Car' },
    'profile.other_bookings': { uk: 'Інші записи',      en: 'Other bookings' },
    'profile.other_bookings_sub': { uk: 'Записи без вказаного конкретного автомобіля', en: 'Bookings without a specific car' },

    // --- Заявки ---
    'book.default_service':   { uk: 'Діагностика / Загальний ремонт', en: 'Diagnostics / General Repair' },
    'book.problem_desc':      { uk: 'Опис проблеми:',   en: 'Problem description:' },
    'book.act_tip':           { uk: 'Переглянути або завантажити Акт виконаних робіт (PDF)', en: 'View or download the work completion act (PDF)' },
    'book.act_pdf':           { uk: 'Акт робіт (PDF)',  en: 'Work Act (PDF)' },
    'book.act_pdf_short':     { uk: 'Акт PDF',          en: 'Act PDF' },
    'book.clients_title':     { uk: 'Заявки клієнтів',  en: 'Client Bookings' },
    'book.clients_sub':       { uk: 'Керуй заявками на ремонт', en: 'Manage repair bookings' },
    'book.f_all':             { uk: 'Все',              en: 'All' },
    'book.f_new':             { uk: 'Нові',             en: 'New' },
    'book.f_confirmed':       { uk: 'В роботі',         en: 'In Progress' },
    'book.f_completed':       { uk: 'Виконано',         en: 'Completed' },
    'book.f_cancelled':       { uk: 'Скасовано',        en: 'Cancelled' },
    'book.none_found':        { uk: 'Заявок не знайдено', en: 'No bookings found' },
    'book.st_new':            { uk: 'Нова',             en: 'New' },
    'book.st_confirmed':      { uk: 'В роботі',         en: 'In Progress' },
    'book.st_completed':      { uk: 'Виконано',         en: 'Completed' },
    'book.st_cancelled':      { uk: 'Скасовано',        en: 'Cancelled' },
    'book.none_at_all':       { uk: 'Наразі немає жодних заявок.', en: 'There are no bookings yet.' },
    'book.problem_label':     { uk: 'Опис проблеми',    en: 'Problem description' },

    // --- Календар ---
    'cal.title':              { uk: 'Календар замовлень', en: 'Booking Calendar' },
    'cal.sub':                { uk: 'Інтерактивний розклад СТО та завантаженість боксів', en: 'Interactive station schedule and box workload' },
    'cal.need_station':       { uk: 'Спочатку створіть або оберіть СТО, щоб переглянути календар.', en: 'Create or select a station first to view the calendar.' },
    'cal.load_error':         { uk: 'Помилка завантаження замовлень для календаря', en: 'Failed to load bookings for the calendar' },
    'cal.confirm_move':       { uk: 'Перенести замовлення на', en: 'Move booking to' },
    'cal.not_moved':          { uk: 'Заявку не перенесено', en: 'Booking was not moved' },
    'cal.booking':            { uk: 'Замовлення',       en: 'Booking' },
    'cal.box':                { uk: 'Бокс',             en: 'Box' },

    // --- Чат заявки ---
    'chat.open_btn':          { uk: 'Чат замовлення',   en: 'Order Chat' },
    'chat.btn':               { uk: 'Чат',              en: 'Chat' },
    'chat.order_chat':        { uk: 'Чат замовлення',   en: 'Order Chat' },
    'chat.modal_sub':         { uk: 'Узгодження деталей та фотофіксація несправностей', en: 'Agree on details and photo-fix the issues' },
    'chat.loading':           { uk: 'Завантаження повідомлень...', en: 'Loading messages...' },
    'chat.cost_label':        { uk: 'Додати додаткові роботи / вартість для узгодження (грн):', en: 'Add extra works/cost for approval (UAH):' },
    'chat.attach_photo_tip':  { uk: 'Прикріпити фото несправності', en: 'Attach a defect photo' },
    'chat.photo_btn':         { uk: 'Фото',             en: 'Photo' },
    'chat.send':              { uk: 'Надіслати',        en: 'Send' },
    'chat.empty':             { uk: 'Немає повідомлень. Почніть діалог!', en: 'No messages yet. Start the conversation!' },
    'chat.from_station':      { uk: 'СТО / Механік',    en: 'Station / Mechanic' },
    'chat.from_client':       { uk: 'Клієнт',           en: 'Client' },
    'chat.approved':          { uk: 'Узгоджено',        en: 'Approved' },
    'chat.declined':          { uk: 'Відхилено',        en: 'Declined' },
    'chat.pending':           { uk: 'Очікує узгодження', en: 'Pending Approval' },
    'chat.approve_btn':       { uk: 'Підтвердити',      en: 'Approve' },
    'chat.decline_btn':       { uk: 'Відхилити',        en: 'Decline' },
    'chat.extra_cost':        { uk: 'Додаткові роботи / деталі', en: 'Extra works/parts' },
    'chat.send_error':        { uk: 'Помилка надсилання повідомлення', en: 'Failed to send message' },
    'chat.approval_error':    { uk: 'Помилка при узгодженні', en: 'Approval error' },

    // --- Склад запчастин ---
    'inv.title':              { uk: 'Склад запчастин та матеріалів', en: 'Parts & Materials Inventory' },
    'inv.sub':                { uk: 'Інвентаризація залишків, облік собівартості та цін продажу', en: 'Stock levels, cost and price tracking' },
    'inv.add_btn':            { uk: 'Додати запчастину', en: 'Add Part' },
    'inv.th_name':            { uk: 'Назва запчастини', en: 'Part Name' },
    'inv.th_qty':             { uk: 'Кількість',        en: 'Quantity' },
    'inv.th_cost':            { uk: 'Собівартість',     en: 'Cost Price' },
    'inv.th_price':           { uk: 'Ціна продажу',     en: 'Selling Price' },
    'inv.th_margin':          { uk: 'Націнка',          en: 'Margin' },
    'inv.th_status':          { uk: 'Статус',           en: 'Status' },
    'inv.out_of_stock':       { uk: 'Немає',            en: 'Out of Stock' },
    'inv.low_stock':          { uk: 'Закінчується',     en: 'Low Stock' },
    'inv.only_stock':         { uk: 'На складі є лише {n} шт цієї деталі.', en: 'Only {n} pcs of this part left in stock.' },
    'inv.confirm_delete':     { uk: 'Видалити цю запчастину зі складу?', en: 'Remove this part from inventory?' },
    'inv.modal_add_title':    { uk: 'Додавання запчастини на склад', en: 'Add Part to Inventory' },
    'inv.lbl_name':           { uk: 'Назва запчастини/матеріалу *', en: 'Part/material name *' },
    'acc.sku':                { uk: 'Артикул',          en: 'SKU' },
    'inv.lbl_sku':            { uk: 'Артикул / Каталожний номер', en: 'SKU / Catalog number' },
    'inv.lbl_qty':            { uk: 'Кількість на складі *', en: 'Quantity in stock *' },
    'inv.lbl_min':            { uk: 'Мін. залишок',     en: 'Min. stock level' },
    'inv.lbl_cost':           { uk: 'Собівартість (грн) *', en: 'Cost price (UAH) *' },
    'inv.lbl_price':          { uk: 'Ціна продажу (грн) *', en: 'Selling price (UAH) *' },
    'inv.save_item':          { uk: 'Зберегти позицію', en: 'Save Item' },
    'inv.modal_edit_title':   { uk: 'Редагування запчастини', en: 'Edit Part' },
    'inv.lbl_cost_short':     { uk: 'Собівартість (грн)', en: 'Cost price (UAH)' },
    'inv.lbl_price_short':    { uk: 'Ціна продажу (грн)', en: 'Selling price (UAH)' },
    'inv.update_item':        { uk: 'Оновити позицію',  en: 'Update Item' },

    // --- Графік роботи ---
    'sched.title':            { uk: 'Графік роботи СТО', en: 'Station Working Hours' },
    'sched.sub':              { uk: 'Налаштування робочих днів, годин відкриття/закриття та обідніх перерв для запису клієнтів', en: 'Set up working days, opening hours and lunch breaks for client bookings' },
    'sched.copy_mon':         { uk: 'Скопіювати Пн на будні (Пн-Пт)', en: 'Copy Mon to weekdays (Mon-Fri)' },
    'sched.working':          { uk: 'Робочий',          en: 'Working' },
    'sched.hours':            { uk: 'Робочий час:',     en: 'Working hours:' },
    'sched.break_label':      { uk: 'Обід:',            en: 'Lunch break:' },
    'sched.save':             { uk: 'Зберегти графік роботи', en: 'Save Schedule' },

    // --- Панель СТО ---
    'station.my_stations':    { uk: 'Мої станції ТО:',  en: 'My stations:' },
    'station.add_another':    { uk: '+ Додати іншу СТО', en: '+ Add another station' },
    'station.view_page':      { uk: 'Переглянути сторінку СТО', en: 'View public page' },
    'station.auto_geo':       { uk: 'Координати на карті визначаються автоматично за адресою', en: 'Map coordinates are set automatically from the address' },
    'station.boxes_title':    { uk: 'Робочі бокси СТО', en: 'Station Work Boxes' },
    'station.boxes_sub':      { uk: 'Керуйте постами та боксами СТО для регулювання завантаженості', en: 'Manage boxes and bays to control the workload' },
    'station.deactivate':     { uk: 'Деактивувати',     en: 'Deactivate' },
    'station.activate':       { uk: 'Активувати',       en: 'Activate' },
    'station.boxes_empty':    { uk: 'Бокси ще не створені. Система автоматично створюватиме один за замовчуванням при першому записі.', en: 'No boxes yet. One default box will be created automatically at the first booking.' },
    'station.add_box_title':  { uk: 'Додати робочий бокс', en: 'Add a Work Box' },
    'station.box_name_label': { uk: 'Назва боксу/поста', en: 'Box/bay name' },
    'station.add_box_btn':    { uk: 'Додати бокс',      en: 'Add Box' },
    'station.services_for':   { uk: 'Послуги для СТО',  en: 'Services for' },
    'station.services_sub':   { uk: 'Керуй переліком послуг цієї конкретної СТО', en: 'Manage services of this particular station' },
    'station.no_services_yet':{ uk: 'Послуг ще немає. Додайте першу послугу для цієї СТО.', en: 'No services yet. Add the first one for this station.' },

    // --- Бухгалтерія: нове ---
    'acc.back_to_garage':     { uk: 'Назад у гараж',    en: 'Back to garage' },
    'acc.tip_theme':          { uk: 'Змінити тему оформлення', en: 'Change color theme' },
    'acc.tip_excel':          { uk: 'Завантажити звіт у форматі Excel (.xlsx)', en: 'Download report as Excel (.xlsx)' },
    'acc.tip_pdf':            { uk: 'Завантажити фінансовий звіт у форматі PDF', en: 'Download financial report as PDF' },
    'acc.tip_preview':        { uk: 'Переглянути PDF-звіт у браузері', en: 'Preview PDF report in browser' },
    'acc.btn_export_excel':   { uk: 'Експорт Excel',    en: 'Export Excel' },
    'acc.btn_export_pdf':     { uk: 'Завантажити PDF',  en: 'Download PDF' },
    'acc.btn_preview_pdf':    { uk: 'Перегляд PDF',     en: 'Preview PDF' },
    'acc.btn_suppliers':      { uk: 'Пошук у постачальників', en: 'Supplier Search' },
    'acc.filter_station':     { uk: 'Обране СТО',       en: 'Selected Station' },
    'acc.filter_period':      { uk: 'Період звітності', en: 'Reporting Period' },
    'acc.filter_type':        { uk: 'Тип операції',     en: 'Transaction Type' },
    'acc.opt_all_tx':         { uk: 'Всі операції',     en: 'All transactions' },
    'acc.opt_income_only':    { uk: 'Тільки доходи',    en: 'Income only' },
    'acc.opt_expense_only':   { uk: 'Тільки витрати',   en: 'Expenses only' },
    'acc.opt_all_cats':       { uk: 'Всі категорії',    en: 'All categories' },
    'acc.opt_all_emps':       { uk: 'Всі співробітники', en: 'All employees' },
    'acc.tbl_name_full':      { uk: 'Співробітник',     en: 'Employee' },
    'acc.tbl_cat_emp':        { uk: 'Категорія та виконавець', en: 'Category & Mechanic' },
    'acc.tbl_purpose':        { uk: 'Призначення платежу', en: 'Payment Purpose' },
    'acc.tbl_paid_date':      { uk: 'Дата виплати',     en: 'Payout Date' },
    'acc.rate_word':          { uk: 'Ставка:',          en: 'Rate:' },
    'acc.commission_word':    { uk: 'Комісія:',         en: 'Commission:' },
    'acc.confirm_fire':       { uk: 'Ви впевнені, що хочете звільнити цього співробітника?', en: 'Fire this employee?' },
    'acc.tip_fire':           { uk: 'Звільнити співробітника', en: 'Fire employee' },
    'acc.booking_word':       { uk: 'Заявка',           en: 'Booking' },
    'acc.no_payouts':         { uk: 'Немає записів про виплати заробітних плат за вказаний період.', en: 'No salary payouts recorded for this period.' },
    'acc.btn_save_emp':       { uk: 'Зберегти працівника', en: 'Save Employee' },
    'acc.chk_reactivate':     { uk: 'Поновити співробітника в штаті СТО', en: 'Reactivate employee' },
    'acc.lbl_rate_short':     { uk: 'Ставка (грн) *',   en: 'Rate (UAH) *' },
    'acc.supplier_modal_title': { uk: 'Пошук та закупівля запчастин у постачальників (InterCars, Exist, TechnoVector)', en: 'Search & purchase parts from suppliers (InterCars, Exist, TechnoVector)' },
    'acc.supplier_all':       { uk: 'Всі постачальники', en: 'All suppliers' },
    'acc.supplier_hint':      { uk: 'Введіть код або назву запчастини та натисніть "Знайти" для перевірки наявності у постачальників.', en: 'Enter a code or part name and hit "Search" to check supplier availability.' },
    'acc.enter_query':        { uk: 'Будь ласка, введіть пошуковий запит.', en: 'Please enter a search query.' },
    'acc.searching':          { uk: 'Пошук у каталогах постачальників...', en: 'Searching supplier catalogs...' },
    'acc.not_found':          { uk: 'Запчастин за даним запитом не знайдено.', en: 'No parts found for this query.' },
    'acc.in_stock':           { uk: 'В наявності',      en: 'In stock' },
    'acc.delivery':           { uk: 'Доставка',         en: 'Delivery' },
    'acc.days':               { uk: 'дн.',              en: 'days' },
    'acc.supplier_word':      { uk: 'Постачальник',     en: 'Supplier' },
    'acc.stock_left':         { uk: 'Залишок:',         en: 'In stock:' },
    'acc.pcs':                { uk: 'шт',               en: 'pcs' },
    'acc.cost_retail':        { uk: 'Закупка / Продаж:', en: 'Purchase / Retail:' },
    'acc.order_to_stock':     { uk: '+ Замовити на склад', en: '+ Order to inventory' },
    'acc.load_error':         { uk: 'Помилка завантаження даних постачальника.', en: 'Failed to load supplier data.' },
    'acc.lbl_mileage':        { uk: 'Пробіг автомобіля (км)', en: 'Car mileage (km)' },
    'acc.lbl_work_list':      { uk: 'Перелік виконаних робіт', en: 'List of performed works' },
    'acc.lbl_parts_manual':   { uk: 'Використані запчастини / матеріали (ручний опис)', en: 'Used spare parts/materials (manual entry)' },
    'acc.lbl_pick_parts':     { uk: 'Вибрати деталі зі складу СТО', en: 'Pick parts from station inventory' },
    'acc.opt_pick_part':      { uk: '-- Оберіть запчастину --', en: '-- Choose a part --' },
    'acc.add_short':          { uk: '+ Додати',         en: '+ Add' },

    // --- Плейсхолдери: нове ---
    'ph.emp_name':            { uk: 'Петро Іванов',     en: 'John Smith' },
    'ph.position':            { uk: 'Автомеханік, Автоелектрик', en: 'Mechanic, Auto Electrician' },
    'ph.tx_comment':          { uk: 'Введіть детальний коментар для журналу...', en: 'Enter a detailed comment for the log...' },
    'ph.supplier_query':      { uk: 'Артикул, OEM-номер або назва (напр. Brembo, колодки, 0986479098)...', en: 'SKU, OEM number or name (e.g. Brembo, brake pads)...' },
    'ph.booking_search':      { uk: 'Пошук за іменем або авто...', en: 'Search by name or car...' },
    'ph.chat_message':        { uk: 'Напишіть повідомлення клієнту/механіку...', en: 'Write a message to the client/mechanic...' },
    'ph.work_list':           { uk: 'Заміна мастила, фільтрів, діагностика ходової...', en: 'Oil change, filters, suspension diagnostics...' },
    'ph.photo_caption':       { uk: "Підпис до фото (необов'язково)", en: 'Photo caption (optional)' },
    'ph.reply_text':          { uk: 'Текст відповіді автосервісу...', en: 'Your reply text...' },
    'ph.review_text':         { uk: 'Розкажіть про свій досвід обслуговування...', en: 'Tell us about your service experience...' },
    'ph.service_example':     { uk: 'Наприклад: Заміна мастила, Діагностика підвіски', en: 'e.g. Oil change, Suspension diagnostics' },
    'ph.problem_desc':        { uk: 'Опишіть симптоми несправності детальніше', en: 'Describe the symptoms in more detail' },
    'ph.box_name':            { uk: 'Бокс 1 (Підйомник)', en: 'Bay 1 (Lift)' },

    'acc.btn_log_tx':         { uk: 'Внести у журнал',  en: 'Add to Log' },
    'acc.filter_category':    { uk: 'Категорія',        en: 'Category' },
    'acc.filter_employee':    { uk: 'Виконавець/Співробітник', en: 'Mechanic/Employee' },
    'acc.tab_payouts':        { uk: 'Архів виплат',     en: 'Payout History' },
    'acc.tab_staff':          { uk: 'Штат та Зарплати', en: 'Staff & Salaries' },
    'common.address':         { uk: 'Адреса',           en: 'Address' },
    'common.phone':           { uk: 'Телефон',          en: 'Phone' },
    'common.deleted_sto':     { uk: 'Видалена СТО',     en: 'Deleted Station' },

    // --- Серверні повідомлення (Django messages) ---
    'msg.m01': { uk: 'Забагато спроб входу. Спробуйте через 5 хвилин.', en: 'Too many attempts. Try again in 5 minutes.' },
    'msg.m02': { uk: 'Ваш акаунт заблоковано.', en: 'Your account has been blocked.' },
    'msg.m03': { uk: 'Невірний email або пароль.', en: 'Invalid email or password.' },
    'msg.m04': { uk: 'Введіть своє ім\'я.', en: 'Please enter your name.' },
    'msg.m05': { uk: 'Невірна роль.', en: 'Invalid role.' },
    'msg.m06': { uk: 'Паролі не збігаються.', en: 'Passwords do not match.' },
    'msg.m07': { uk: 'Такий email вже зареєстровано.', en: 'This email is already registered.' },
    'msg.m08': { uk: 'Такий телефон вже використовується.', en: 'This phone number is already in use.' },
    'msg.m09': { uk: 'Реєстрація успішна! Ласкаво просимо.', en: 'Registration successful! Welcome aboard.' },
    'msg.m10': { uk: 'Ім\'я не може бути порожнім.', en: 'Name cannot be empty.' },
    'msg.m11': { uk: 'Цей номер телефону вже використовується.', en: 'This phone number is already taken.' },
    'msg.m12': { uk: 'Дані успішно оновлено.', en: 'Details updated successfully.' },
    'msg.m13': { uk: 'Поточний пароль введено невірно.', en: 'Current password is incorrect.' },
    'msg.m14': { uk: 'Нові паролі не збігаються.', en: 'New passwords do not match.' },
    'msg.m15': { uk: 'Пароль успішно змінено.', en: 'Password changed successfully.' },
    'msg.m16': { uk: 'Спочатку оберіть або створіть СТО.', en: 'Select or create a station first.' },
    'msg.m17': { uk: 'Графік роботи СТО успішно збережено.', en: 'Working schedule saved successfully.' },
    'msg.m18': { uk: 'Ця дія доступна тільки клієнтам.', en: 'This action is available to clients only.' },
    'msg.m19': { uk: 'Невірний VIN-код. Має бути 17 символів.', en: 'Invalid VIN code. It must be exactly 17 characters.' },
    'msg.m20': { uk: 'Введіть марку та модель автомобіля.', en: 'Enter the car make and model.' },
    'msg.m21': { uk: 'Автомобіль з таким VIN вже зареєстровано.', en: 'A car with this VIN is already registered.' },
    'msg.m22': { uk: 'Автомобіль видалено.', en: 'Car deleted.' },
    'msg.m23': { uk: 'Автомобіль не знайдено.', en: 'Car not found.' },
    'msg.m24': { uk: 'Фото автомобіля оновлено.', en: 'Car photo updated.' },
    'msg.m25': { uk: 'Ця дія доступна тільки власникам СТО.', en: 'This action is available to station owners only.' },
    'msg.m26': { uk: 'Назва та адреса СТО обов\'язкові.', en: 'Station name and address are required.' },
    'msg.m27': { uk: 'Дані СТО оновлено.', en: 'Station details updated.' },
    'msg.m28': { uk: 'Нову СТО успішно створено.', en: 'New station created successfully.' },
    'msg.m29': { uk: 'Спочатку заповніть профіль СТО.', en: 'Fill in the station profile first.' },
    'msg.m30': { uk: 'Введіть назву послуги.', en: 'Enter the service name.' },
    'msg.m31': { uk: 'Ціна має бути числом більше 0.', en: 'Price must be a number greater than 0.' },
    'msg.m32': { uk: 'Послугу видалено.', en: 'Service deleted.' },
    'msg.m33': { uk: 'Послугу не знайдено.', en: 'Service not found.' },
    'msg.m34': { uk: 'Робочий бокс успішно додано.', en: 'Work box added successfully.' },
    'msg.m35': { uk: 'Робочий бокс видалено.', en: 'Work box deleted.' },
    'msg.m36': { uk: 'Аватар оновлено.', en: 'Avatar updated.' },
    'msg.m37': { uk: 'Неможливо оновити статус.', en: 'Unable to update the status.' },
    'msg.m38': { uk: 'Доступ заборонено.', en: 'Access denied.' },
    'msg.m39': { uk: 'Клієнта не знайдено.', en: 'Client not found.' },
    'msg.m40': { uk: 'Доступ заборонено: у клієнта немає заявок на вашій СТО.', en: 'Access denied: this client has no bookings at your station.' },
    'msg.m41': { uk: 'У вас немає прав для перегляду документа.', en: 'You do not have permission to view this document.' },
    'msg.m42': { uk: 'Будь ласка, спочатку створіть СТО в профілі.', en: 'Please create a station in your profile first.' },
    'msg.m43': { uk: 'Ім\'я та посада є обов\'язковими.', en: 'Name and position are required.' },
    'msg.m44': { uk: 'Сума виплати має бути більшою за нуль.', en: 'Payout amount must be greater than zero.' },
    'msg.m45': { uk: 'Помилка при виплаті зарплати.', en: 'Salary payout error.' },
    'msg.m46': { uk: 'Невірний тип операції.', en: 'Invalid transaction type.' },
    'msg.m47': { uk: 'Невірна категорія операції.', en: 'Invalid transaction category.' },
    'msg.m48': { uk: 'Сума має бути більшою за нуль.', en: 'Amount must be greater than zero.' },
    'msg.m49': { uk: 'Невірний формат дати. Використовуйте РРРР-ММ-ДД.', en: 'Invalid date format. Use YYYY-MM-DD.' },
    'msg.m50': { uk: 'Операцію успішно додано.', en: 'Transaction added successfully.' },
    'msg.m51': { uk: 'Вартість ремонту повинна бути більшою за нуль.', en: 'Repair cost must be greater than zero.' },
    'msg.m52': { uk: 'Заявку не знайдено.', en: 'Booking not found.' },
    'msg.m53': { uk: 'Помилка при завершенні ремонту.', en: 'Error while completing the repair.' },
    'msg.m54': { uk: 'Вкажіть назву запчастини.', en: 'Enter the part name.' },
    'msg.m55': { uk: 'Не вказано СТО для експорту.', en: 'No station selected for export.' },
    'msg.m56': { uk: 'Спочатку створіть СТО.', en: 'Create a station first.' },
    'msg.m57': { uk: 'Назва запчастини є обов\'язковою.', en: 'Part name is required.' },
    'msg.m58': { uk: 'Увійдіть в акаунт, щоб залишити відгук.', en: 'Sign in to leave a review.' },
    'msg.m59': { uk: 'Тільки клієнти можуть залишати відгуки.', en: 'Only clients can leave reviews.' },
    'msg.m60': { uk: 'Введіть текст відгуку.', en: 'Enter your review text.' },
    'msg.m61': { uk: 'Оцінка має бути від 1 до 5.', en: 'Rating must be between 1 and 5.' },
    'msg.m62': { uk: 'Дякуємо за відгук!', en: 'Thanks for your review!' },
    'msg.m63': { uk: 'Тільки власник СТО може відповідати на відгуки.', en: 'Only the station owner can reply to reviews.' },
    'msg.m64': { uk: 'Відповідь успішно збережено.', en: 'Reply saved successfully.' },
    'msg.m65': { uk: 'Введіть текст відповіді.', en: 'Enter your reply text.' },
    'msg.m66': { uk: 'Тільки власник може завантажувати фото.', en: 'Only the owner can upload photos.' },
    'msg.m67': { uk: 'Фото завантажено.', en: 'Photo uploaded.' },
    'msg.m68': { uk: 'Тільки власник може видаляти фото.', en: 'Only the owner can delete photos.' },
    'msg.m69': { uk: 'Фото видалено.', en: 'Photo deleted.' },
    'msg.m70': { uk: 'Фото не знайдено.', en: 'Photo not found.' },
    'msg.m71': { uk: 'Ваш аккаунт був заблокований адміністратором.', en: 'Your account has been blocked by the administrator.' },
    'msg.m72': { uk: 'Увійдіть в акаунт, щоб отримати доступ до цієї сторінки.', en: 'Sign in to access this page.' },
    'msg.m73': { uk: 'У вас немає доступу до цієї дії.', en: 'You do not have permission for this action.' },
    'msg.m74': { uk: 'Оберіть файл для завантаження.', en: 'Choose a file to upload.' },
    'msg.m75': { uk: 'Дозволені лише зображення (JPEG, PNG, WebP, GIF).', en: 'Only images are allowed (JPEG, PNG, WebP, GIF).' },
    'msg.m76': { uk: 'Розмір файлу перевищує 3 МБ.', en: 'File size exceeds 3 MB.' },
    'msg.m77': { uk: 'Недостатньо запчастини на складі.', en: 'Not enough parts in stock.' },
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

// Отримати переклад за ключем (для динамічних рядків у JS)
function t(key, lang) {
    const entry = TRANSLATIONS[key];
    if (!entry) return key;
    return entry[lang || getLang()] !== undefined ? entry[lang || getLang()] : entry.uk;
}

function applyTranslations(lang) {
    lang = lang || getLang();

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

    // Підказки (атрибут title) на будь-яких елементах
    document.querySelectorAll('[data-i18n-tip]').forEach(el => {
        const key = el.getAttribute('data-i18n-tip');
        if (TRANSLATIONS[key] && TRANSLATIONS[key][lang] !== undefined) {
            el.title = TRANSLATIONS[key][lang];
        }
    });

    // Атрибут aria-label для доступності
    document.querySelectorAll('[data-i18n-aria]').forEach(el => {
        const key = el.getAttribute('data-i18n-aria');
        if (TRANSLATIONS[key] && TRANSLATIONS[key][lang] !== undefined) {
            el.setAttribute('aria-label', TRANSLATIONS[key][lang]);
        }
    });

    // Заголовок вкладки браузера
    const titleEl = document.querySelector('[data-i18n-title]');
    if (titleEl) {
        const key = titleEl.getAttribute('data-i18n-title');
        if (TRANSLATIONS[key] && TRANSLATIONS[key][lang] !== undefined) {
            document.title = TRANSLATIONS[key][lang];
        }
    }

    // Серверні повідомлення (Django messages) перекладаємо за точним збігом тексту
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

// Переклад фрагмента, доданого динамічно (після рендеру в JS)
function applyTranslationsTo(root) {
    const lang = getLang();
    if (lang === 'uk' || !root) return;

    root.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (TRANSLATIONS[key] && TRANSLATIONS[key][lang] !== undefined) {
            el.textContent = TRANSLATIONS[key][lang];
        }
    });
    root.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (TRANSLATIONS[key] && TRANSLATIONS[key][lang] !== undefined) {
            el.placeholder = TRANSLATIONS[key][lang];
        }
    });

    if (root.matches && root.matches('[data-i18n]')) {
        const key = root.getAttribute('data-i18n');
        if (TRANSLATIONS[key] && TRANSLATIONS[key][lang] !== undefined) {
            root.textContent = TRANSLATIONS[key][lang];
        }
    }
}

window.t = t;
window.applyTranslations = applyTranslations;
window.applyTranslationsTo = applyTranslationsTo;
window.getLang = getLang;

// Автопереклад контенту, який з'являється на сторінці пізніше (чати, списки заявок тощо)
const _i18nObserver = new MutationObserver(mutations => {
    if (getLang() === 'uk') return;
    for (const m of mutations) {
        m.addedNodes.forEach(node => {
            if (node.nodeType === Node.ELEMENT_NODE) {
                applyTranslationsTo(node);
            }
        });
    }
});

function initLangSelect() {
    const select = document.getElementById('lang-select');
    if (!select) return;

    const currentLang = getLang();
    select.value = currentLang;

    // Мобільний селект синхронізується з десктопним у navigation.js
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
    _i18nObserver.observe(document.body, { childList: true, subtree: true });
});
