import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable, Image, LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

FONT_FAMILY = 'KarroRegular'
FONT_BOLD = 'KarroBold'

INK = colors.HexColor('#1e293b')
MUTED = colors.HexColor('#64748b')
BORDER = colors.HexColor('#cbd5e1')
PALE = colors.HexColor('#f8fafc')
BLUE = colors.HexColor('#2563eb')


def register_cyrillic_fonts():
    """Реєструє шрифт DejaVu або Arial для коректного відображення кирилиці."""
    reg = pdfmetrics.getRegisteredFontNames()
    if FONT_FAMILY in reg and FONT_BOLD in reg:
        return

    font_dirs = [
        Path(settings.BASE_DIR) / 'static' / 'fonts',
        Path(settings.BASE_DIR) / 'fonts',
        Path('/usr/share/fonts/truetype/dejavu'),
        Path('/usr/share/fonts/dejavu'),
        Path('/usr/share/fonts/truetype/liberation2'),
        Path('C:/Windows/Fonts'),
        Path('/Library/Fonts'),
    ]
    font_pairs = [
        ('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf'),
        ('LiberationSans-Regular.ttf', 'LiberationSans-Bold.ttf'),
        ('arial.ttf', 'arialbd.ttf'),
        ('Arial.ttf', 'Arial Bold.ttf'),
    ]

    for d in font_dirs:
        for reg_name, bold_name in font_pairs:
            r_path, b_path = d / reg_name, d / bold_name
            if not r_path.is_file():
                continue
            if not b_path.is_file():
                b_path = r_path
            try:
                if FONT_FAMILY not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(FONT_FAMILY, str(r_path)))
                if FONT_BOLD not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(b_path)))
                pdfmetrics.registerFontFamily(FONT_FAMILY, normal=FONT_FAMILY, bold=FONT_BOLD, italic=FONT_FAMILY, boldItalic=FONT_BOLD)
                return
            except (OSError, ValueError):
                continue

    if FONT_FAMILY not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFontFamily('Helvetica', normal='Helvetica', bold='Helvetica-Bold')


def _fonts():
    register_cyrillic_fonts()
    reg = pdfmetrics.getRegisteredFontNames()
    if FONT_FAMILY in reg and FONT_BOLD in reg:
        return FONT_FAMILY, FONT_BOLD
    return 'Helvetica', 'Helvetica-Bold'


def _text(val):
    return escape(str(val if val is not None else '')).replace('\n', '<br/>')


def _money(val):
    try:
        amt = Decimal(str(val))
        if amt.is_finite():
            return amt.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        pass
    return Decimal('0.00')


def _money_str(val):
    return f'{_money(val):,.2f}'.replace(',', ' ')


def _form(num, one, few, many):
    last_two, last_d = num % 100, num % 10
    if 11 <= last_two <= 14:
        return many
    if last_d == 1:
        return one
    if 2 <= last_d <= 4:
        return few
    return many


_UNITS = ('', 'один', 'два', 'три', 'чотири', "п'ять", 'шість', 'сім', 'вісім', "дев'ять",
          'десять', 'одинадцять', 'дванадцять', 'тринадцять', 'чотирнадцять', "п'ятнадцять",
          'шістнадцять', 'сімнадцять', 'вісімнадцять', "дев'ятнадцять")
_TENS = ('', '', 'двадцять', 'тридцять', 'сорок', "п'ятдесят", 'шістдесят', 'сімдесят', 'вісімдесят', "дев'яносто")
_HUNDREDS = ('', 'сто', 'двісті', 'триста', 'чотириста', "п'ятсот", 'шістсот', 'сімсот', 'вісімсот', "дев'ятсот")
_GROUPS = (
    None,
    ('тисяча', 'тисячі', 'тисяч', True),
    ('мільйон', 'мільйони', 'мільйонів', False),
    ('мільярд', 'мільярди', 'мільярдів', False),
)


def _group_to_words(num, feminine=False):
    words = []
    h, rem = divmod(num, 100)
    if h:
        words.append(_HUNDREDS[h])
    if rem >= 20:
        t, u = divmod(rem, 10)
        words.append(_TENS[t])
    else:
        u = rem
    if u:
        if feminine and u == 1:
            words.append('одна')
        elif feminine and u == 2:
            words.append('дві')
        else:
            words.append(_UNITS[u])
    return words


def number_to_words_ua(val):
    """Конвертація суми в гривнях у прописний рядок українською мовою."""
    try:
        amt = Decimal(str(val))
        if not amt.is_finite():
            raise InvalidOperation
        amt = amt.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return f'{val} грн'

    sign = 'Мінус ' if amt < 0 else ''
    hryvnias, kopecks = divmod(int(abs(amt) * 100), 100)
    if hryvnias == 0:
        words = ['нуль']
    else:
        words, groups, rest = [], [], hryvnias
        while rest:
            rest, g = divmod(rest, 1000)
            groups.append(g)
        for idx in range(len(groups) - 1, -1, -1):
            g = groups[idx]
            if not g:
                continue
            g_info = _GROUPS[idx] if idx < len(_GROUPS) else None
            fem = (idx == 0) or (g_info is not None and g_info[3])
            words.extend(_group_to_words(g, fem))
            if g_info:
                words.append(_form(g, *g_info[:3]))

    curr = _form(hryvnias, 'гривня', 'гривні', 'гривень')
    kop = _form(kopecks, 'копійка', 'копійки', 'копійок')
    res = ' '.join(words)
    if not sign:
        res = res.capitalize()
    return f'{sign}{res} {curr} {kopecks:02d} {kop}'


class NumberedCanvas(canvas.Canvas):
    """Нумерація сторінок та нижній колонтитул документа."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pages = []

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        count = len(self._pages)
        for page in self._pages:
            self.__dict__.update(page)
            self._draw_footer(count)
            super().showPage()
        super().save()

    def _draw_footer(self, count):
        regular, _ = _fonts()
        self.saveState()
        self.setStrokeColor(BORDER)
        self.line(12 * mm, 12 * mm, A4[0] - 12 * mm, 12 * mm)
        self.setFillColor(MUTED)
        self.setFont(regular, 8)
        self.drawString(12 * mm, 7 * mm, 'Згенеровано в системі Karro')
        self.drawRightString(A4[0] - 12 * mm, 7 * mm, f'Сторінка {self._pageNumber} з {count}')
        self.restoreState()


def get_pdf_styles():
    regular, bold = _fonts()
    normal = getSampleStyleSheet()['Normal']
    return {
        'title': ParagraphStyle('KTitle', parent=normal, fontName=bold, fontSize=14, leading=18, textColor=INK),
        'subtitle': ParagraphStyle('KSubtitle', parent=normal, fontName=regular, fontSize=8.5, leading=11, textColor=MUTED),
        'h2': ParagraphStyle('KH2', parent=normal, fontName=bold, fontSize=10.5, leading=13, textColor=INK, spaceBefore=8, spaceAfter=4),
        'body': ParagraphStyle('KBody', parent=normal, fontName=regular, fontSize=8, leading=11, textColor=INK),
        'bold': ParagraphStyle('KBold', parent=normal, fontName=bold, fontSize=8, leading=11, textColor=INK),
        'header': ParagraphStyle('KHeader', parent=normal, fontName=bold, fontSize=8, leading=10, textColor=colors.white),
        'cell': ParagraphStyle('KCell', parent=normal, fontName=regular, fontSize=8, leading=10, textColor=INK),
    }


def _p(val, style):
    return Paragraph(_text(val), style)


def _table(rows, widths, *, header=False):
    t = LongTable(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign='LEFT')
    cmd = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.4, BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]
    if header:
        cmd.extend([
            ('BACKGROUND', (0, 0), (-1, 0), INK),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, PALE]),
        ])
    t.setStyle(TableStyle(cmd))
    return t


def _logo(station, styles):
    if station and station.logo:
        try:
            with station.logo.open('rb') as f:
                return Image(BytesIO(f.read()), width=38 * mm, height=15 * mm, lazy=0)
        except (OSError, ValueError):
            pass
    name = station.name if station else 'СТО'
    return _p(f'[{name[:2].upper()}] Karro', styles['title'])


def _act_date(booking):
    dt = getattr(booking, 'created_at', None)
    if not dt:
        return timezone.localdate().strftime('%d.%m.%Y')
    if isinstance(dt, datetime.datetime) and timezone.is_aware(dt):
        dt = timezone.localtime(dt)
    return dt.strftime('%d.%m.%Y') if hasattr(dt, 'strftime') else str(dt)


def generate_act_pdf(booking):
    """Повертає акт виконаних робіт у форматі PDF (байтовий масив)."""
    styles = get_pdf_styles()
    story = []
    station, client, car = booking.station, booking.client, booking.car
    history = booking.car_history_records.order_by('-date', '-pk').first()

    st_name = str(station.name) if (station and getattr(station, 'name', None)) else 'Автосервіс'
    st_info = [st_name, f'Адреса: {station.address}' if station else 'Адреса: не вказана']
    if station and getattr(station, 'phone', None):
        st_info.append(f'Тел: {station.phone}')
    if station and getattr(station, 'edrpou', None):
        st_info.append(f'ЄДРПОУ: {station.edrpou}')
    if station and getattr(station, 'bank_details', None):
        st_info.append(f'Р/р: {station.bank_details}')

    header = Table([[_logo(station, styles), _p('\n'.join(str(x) for x in st_info), styles['body'])]], colWidths=[44 * mm, 142 * mm])
    header.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 0)]))

    story.extend([
        header, Spacer(1, 3 * mm),
        HRFlowable(width='100%', thickness=1, color=BORDER), Spacer(1, 4 * mm),
        _p(f'АКТ ВИКОНАНИХ РОБІТ № ACT-{booking.pk:05d}', styles['title']),
        _p(f'Від {_act_date(booking)} · Статус: {booking.get_status_display()}', styles['subtitle']),
        Spacer(1, 4 * mm),
    ])

    car_name = f'{car.brand} {car.model} ({car.year})' if car else 'Не вказано'
    mileage = f'{history.mileage:,} км'.replace(',', ' ') if history and history.mileage is not None else 'Не вказано'
    cl_name = client.full_name if client else 'Клієнт'
    cl_phone = client.phone if client and client.phone else '—'

    details = [
        [_p('Замовник', styles['bold']), _p(cl_name, styles['body']), _p('Автомобіль', styles['bold']), _p(car_name, styles['body'])],
        [_p('Телефон', styles['bold']), _p(cl_phone, styles['body']), _p('VIN-код', styles['bold']), _p(car.vin_code if car else '—', styles['body'])],
        [_p('Опис', styles['bold']), _p(booking.description or '—', styles['body']), _p('Пробіг', styles['bold']), _p(mileage, styles['body'])],
    ]
    story.append(_table(details, [26 * mm, 67 * mm, 26 * mm, 67 * mm]))

    # Запчастини
    part_items, parts_total = [], Decimal('0.00')
    for part in booking.used_parts.select_related('spare_part'):
        p_name = part.part_name + (f' (арт. {part.spare_part.sku})' if part.spare_part and part.spare_part.sku else '')
        price = _money(part.selling_price)
        part_items.append((p_name, part.quantity, price))
        parts_total += price * part.quantity

    # Послуги
    approved = list(booking.chat_messages.filter(is_approved=True, proposed_cost__gt=0).order_by('pk'))
    extra_total = sum((_money(m.proposed_cost) for m in approved), Decimal('0.00'))
    service_items = [
        (m.text.strip() if m.text and m.text.strip() else 'Додаткова погоджена робота', 1, _money(m.proposed_cost))
        for m in approved
    ]
    base_price = (_money(history.price) - parts_total - extra_total) if history else Decimal('0.00')
    base_name = booking.service_name or (history.work_list if history and history.work_list else '') or 'Технічне обслуговування'
    service_items.insert(0, (base_name, 1, base_price if base_price >= 0 else Decimal('0.00')))
    services_total = sum((p * q for _, q, p in service_items), Decimal('0.00'))
    grand_total = services_total + parts_total

    def build_rows(items):
        r = [[_p(h, styles['header']) for h in ['№', 'Найменування', 'К-сть', 'Ціна, грн', 'Сума, грн']]]
        for i, (name, q, price) in enumerate(items, 1):
            r.append([_p(i, styles['cell']), _p(name, styles['cell']), _p(q, styles['cell']),
                      _p(_money_str(price), styles['cell']), _p(_money_str(price * q), styles['cell'])])
        return r

    story.append(_p('1. Виконані роботи', styles['h2']))
    story.append(_table(build_rows(service_items), [10 * mm, 105 * mm, 17 * mm, 27 * mm, 27 * mm], header=True))

    story.append(_p('2. Використані запчастини', styles['h2']))
    if not part_items:
        part_items = [('Запчастини не використовувалися', 0, Decimal('0.00'))]
    story.append(_table(build_rows(part_items), [10 * mm, 105 * mm, 17 * mm, 27 * mm, 27 * mm], header=True))

    story.append(Spacer(1, 4 * mm))
    totals = [
        [_p('Роботи', styles['body']), _p(f'{_money_str(services_total)} грн', styles['bold'])],
        [_p('Запчастини', styles['body']), _p(f'{_money_str(parts_total)} грн', styles['bold'])],
        [_p('УСЬОГО ДО СПЛАТИ', styles['bold']), _p(f'{_money_str(grand_total)} грн', styles['bold'])],
    ]
    t_table = _table(totals, [130 * mm, 56 * mm])
    t_table.setStyle(TableStyle([('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#eff6ff'))]))
    story.extend([
        t_table, Spacer(1, 3 * mm),
        _p(f'Сума прописом: {number_to_words_ua(grand_total)}', styles['body']),
        Spacer(1, 5 * mm),
        _p('Умови та гарантія: роботи виконані в зазначеному обсязі. Гарантія на виконані роботи — 30 днів або 2 000 км пробігу.', styles['subtitle']),
        Spacer(1, 6 * mm),
        Table([
            [_p('ВИКОНАВЕЦЬ', styles['bold']), _p('ЗАМОВНИК', styles['bold'])],
            [_p(f'{st_name}\n\n________________________', styles['body']), _p(f'{cl_name}\n\n________________________', styles['body'])],
        ], colWidths=[93 * mm, 93 * mm]),
    ])

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=16 * mm)
    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()


def generate_financial_report_pdf(station, start_date, end_date, transactions, metrics, employees):
    """Повертає фінансовий звіт СТО у форматі PDF (байтовий масив)."""
    styles = get_pdf_styles()
    transactions, employees = list(transactions), list(employees)
    story = []

    title = Table([[_logo(station, styles), _p(f'ФІНАНСОВИЙ ЗВІТ: {station.name if station else "СТО"}', styles['title'])]], colWidths=[44 * mm, 142 * mm])
    title.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 0)]))

    story.extend([
        title, Spacer(1, 3 * mm),
        _p(f'Період: {start_date:%d.%m.%Y} — {end_date:%d.%m.%Y}', styles['subtitle']), Spacer(1, 3 * mm),
        HRFlowable(width='100%', thickness=1, color=BLUE), Spacer(1, 4 * mm),
    ])

    inc, exp = _money(metrics.get('total_income', 0)), _money(metrics.get('total_expense', 0))
    prof, margin = _money(metrics.get('net_profit', inc - exp)), metrics.get('profit_margin', 0)
    summary = [
        [_p('Дохід', styles['bold']), _p('Витрати', styles['bold']), _p('Чистий результат', styles['bold']), _p('Рентабельність', styles['bold'])],
        [_p(f'{_money_str(inc)} грн', styles['body']), _p(f'{_money_str(exp)} грн', styles['body']), _p(f'{_money_str(prof)} грн', styles['body']), _p(f'{margin:.1f} %', styles['body'])],
    ]
    story.append(_table(summary, [46.5 * mm] * 4))

    inc_cats, exp_cats = list(metrics.get('income_by_category', {}).items()), list(metrics.get('expense_by_category', {}).items())
    story.append(_p('Доходи та витрати за категоріями', styles['h2']))
    cat_rows = [[_p('Категорія доходу', styles['header']), _p('Сума, грн', styles['header']), _p('Категорія витрати', styles['header']), _p('Сума, грн', styles['header'])]]
    for i in range(max(len(inc_cats), len(exp_cats), 1)):
        i_n, i_a = inc_cats[i] if i < len(inc_cats) else ('—', 0)
        e_n, e_a = exp_cats[i] if i < len(exp_cats) else ('—', 0)
        cat_rows.append([_p(i_n, styles['cell']), _p(_money_str(i_a), styles['cell']), _p(e_n, styles['cell']), _p(_money_str(e_a), styles['cell'])])
    story.append(_table(cat_rows, [57 * mm, 36 * mm, 57 * mm, 36 * mm], header=True))

    if employees:
        story.append(_p('Працівники та зарплатний баланс', styles['h2']))
        emp_rows = [[_p(h, styles['header']) for h in ['Працівник', 'Посада', 'Ставка', 'Комісія', 'Зароблено', 'Виплачено', 'Залишок']]]
        for emp in employees:
            bal = getattr(emp, 'salary_balance', None)
            earned = bal.total_earned if bal else 0
            paid = bal.total_paid if bal else 0
            rem = bal.current_balance if bal else 0
            emp_rows.append([_p(emp.full_name, styles['cell']), _p(emp.position, styles['cell']), _p(_money_str(emp.base_salary), styles['cell']),
                            _p(f'{emp.commission_percent} %', styles['cell']), _p(_money_str(earned), styles['cell']), _p(_money_str(paid), styles['cell']), _p(_money_str(rem), styles['cell'])])
        story.append(_table(emp_rows, [38 * mm, 27 * mm, 24 * mm, 20 * mm, 26 * mm, 26 * mm, 25 * mm], header=True))

    story.append(_p(f'Фінансові операції: {len(transactions)}', styles['h2']))
    tx_rows = [[_p(h, styles['header']) for h in ['Дата', 'Тип', 'Категорія', 'Опис', 'Сума, грн']]]
    for tx in transactions:
        tx_rows.append([_p(tx.date.strftime('%d.%m.%Y'), styles['cell']), _p(tx.get_type_display(), styles['cell']),
                        _p(tx.get_category_display(), styles['cell']), _p(tx.description or '—', styles['cell']), _p(_money_str(tx.amount), styles['cell'])])
    if not transactions:
        tx_rows.append([_p('—', styles['cell']), _p('—', styles['cell']), _p('—', styles['cell']), _p('Операцій за цей період немає', styles['cell']), _p('0,00', styles['cell'])])
    story.append(_table(tx_rows, [24 * mm, 22 * mm, 38 * mm, 68 * mm, 34 * mm], header=True))

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=16 * mm)
    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()
