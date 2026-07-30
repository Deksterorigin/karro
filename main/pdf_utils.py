import os
import io
import datetime
from decimal import Decimal

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_FAMILY = 'ArialCyr'
FONT_BOLD = 'ArialCyr-Bold'


def register_cyrillic_fonts():
    """Реєстрація системних або локальних шрифтів Arial для кирилиці в PDF."""
    if FONT_FAMILY in pdfmetrics.getRegisteredFontNames():
        return

    font_path_regular = 'C:/Windows/Fonts/arial.ttf'
    font_path_bold = 'C:/Windows/Fonts/arialbd.ttf'

    if os.path.exists(font_path_regular):
        pdfmetrics.registerFont(TTFont(FONT_FAMILY, font_path_regular))
    else:
        fallback_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'static', 'fonts', 'arial.ttf'
        )
        if os.path.exists(fallback_path):
            pdfmetrics.registerFont(TTFont(FONT_FAMILY, fallback_path))

    if os.path.exists(font_path_bold):
        pdfmetrics.registerFont(TTFont(FONT_BOLD, font_path_bold))
    elif FONT_FAMILY in pdfmetrics.getRegisteredFontNames():
        fallback_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'fonts', 'arial.ttf')
        reg_path = font_path_regular if os.path.exists(font_path_regular) else fallback_path
        pdfmetrics.registerFont(TTFont(FONT_BOLD, reg_path))


register_cyrillic_fonts()


class NumberedCanvas(canvas.Canvas):
    """Полотно для двопрохідного рендерингу нумерації сторінок та нижнього футера."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont(FONT_FAMILY, 8)
        self.setFillColor(colors.HexColor('#64748b'))

        # Тонка лінія над колонтитулом
        self.setStrokeColor(colors.HexColor('#cbd5e1'))
        self.setLineWidth(0.5)
        self.line(15 * mm, 12 * mm, A4[0] - 15 * mm, 12 * mm)

        footer_text = "Згенеровано системою обліку СТО • Документ є офіційним актом виконаних робіт"
        page_str = f"Сторінка {self._pageNumber} з {page_count}"

        self.drawString(15 * mm, 7 * mm, footer_text)
        self.drawRightString(A4[0] - 15 * mm, 7 * mm, page_str)
        self.restoreState()


def number_to_words_ua(number_val):
    """Конвертація суми в гривнях у прописний текст українською мовою."""
    try:
        val = Decimal(str(number_val))
    except Exception:
        return f"{number_val} грн"

    units = [
        "", "одна", "дві", "три", "чотири", "п'ять", "шість", "сім", "вісім", "дев'ять",
        "десять", "одинадцять", "дванадцять", "тринадцять", "чотирнадцять",
        "п'ятнадцять", "шістнадцять", "сімнадцять", "вісімнадцять", "дев'ятнадцять"
    ]
    tens = ["", "", "двадцять", "тридцять", "сорок", "п'ятдесят", "шістьдесят", "сімдесят", "вісімдесят", "дев'яносто"]
    hundreds = ["", "сто", "двісті", "триста", "чотириста", "п'ятсот", "шістсот", "сімсот", "вісімсот", "дев'ятсот"]

    int_part = int(val)
    kop_part = int(round((val - int_part) * 100))

    if int_part == 0:
        words = "нуль"
    else:
        parts = []

        def _convert_group(n, feminine=False):
            group_parts = []
            h, t, u = n // 100, (n % 100) // 10, n % 10
            if h > 0:
                group_parts.append(hundreds[h])
            if t == 1:
                group_parts.append(units[10 + u])
            else:
                if t > 0:
                    group_parts.append(tens[t])
                if u > 0:
                    if feminine and u == 1:
                        group_parts.append("одна")
                    elif feminine and u == 2:
                        group_parts.append("дві")
                    else:
                        group_parts.append(units[u])
            return group_parts

        millions = (int_part // 1_000_000) % 1000
        if millions > 0:
            parts.extend(_convert_group(millions))
            m_two, m_one = millions % 100, millions % 10
            parts.append("мільйонів" if 11 <= m_two <= 19 else ("мільйон" if m_one == 1 else ("мільйони" if m_one in [2, 3, 4] else "мільйонів")))

        thousands = (int_part // 1000) % 1000
        if thousands > 0:
            parts.extend(_convert_group(thousands, feminine=True))
            t_two, t_one = thousands % 100, thousands % 10
            parts.append("тисяч" if 11 <= t_two <= 19 else ("тисяча" if t_one == 1 else ("тисячі" if t_one in [2, 3, 4] else "тисяч")))

        rem = int_part % 1000
        if rem > 0:
            parts.extend(_convert_group(rem, feminine=True))

        words = " ".join(parts).strip()

    words = words.capitalize()
    last_two, last_one = int_part % 100, int_part % 10
    currency_str = "гривень" if 11 <= last_two <= 19 else ("гривня" if last_one == 1 else ("гривні" if last_one in [2, 3, 4] else "гривень"))

    return f"{words} {currency_str} {kop_part:02d} копійок"


def get_pdf_styles():
    """Базові стилі ReportLab для актів та фінансових звітів."""
    styles = getSampleStyleSheet()

    return {
        'title': ParagraphStyle('DocTitle', parent=styles['Normal'], fontName=FONT_BOLD, fontSize=16, leading=20, textColor=colors.HexColor('#0f172a')),
        'subtitle': ParagraphStyle('DocSubtitle', parent=styles['Normal'], fontName=FONT_FAMILY, fontSize=9, leading=12, textColor=colors.HexColor('#475569')),
        'h2': ParagraphStyle('SectionHeading', parent=styles['Normal'], fontName=FONT_BOLD, fontSize=11, leading=14, textColor=colors.HexColor('#1e293b'), spaceBefore=8, spaceAfter=4),
        'body': ParagraphStyle('BodyTextCustom', parent=styles['Normal'], fontName=FONT_FAMILY, fontSize=8.5, leading=11, textColor=colors.HexColor('#1e293b')),
        'body_bold': ParagraphStyle('BodyBoldCustom', parent=styles['Normal'], fontName=FONT_BOLD, fontSize=8.5, leading=11, textColor=colors.HexColor('#0f172a')),
        'table_header': ParagraphStyle('TableHeader', parent=styles['Normal'], fontName=FONT_BOLD, fontSize=8.5, leading=11, textColor=colors.HexColor('#ffffff')),
        'table_cell': ParagraphStyle('TableCell', parent=styles['Normal'], fontName=FONT_FAMILY, fontSize=8, leading=10, textColor=colors.HexColor('#1e293b')),
        'table_cell_bold': ParagraphStyle('TableCellBold', parent=styles['Normal'], fontName=FONT_BOLD, fontSize=8, leading=10, textColor=colors.HexColor('#0f172a')),
        'badge': ParagraphStyle('BadgeText', parent=styles['Normal'], fontName=FONT_BOLD, fontSize=9, leading=11, textColor=colors.HexColor('#2563eb'), alignment=2),
    }


def generate_act_pdf(booking):
    """Генерація Акта виконаних робіт у форматах PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=12*mm, rightMargin=12*mm, topMargin=12*mm, bottomMargin=16*mm)
    st = get_pdf_styles()
    story = []

    station, client, car = booking.station, booking.client, booking.car

    # 1. Шапка СТО
    logo_flowable = None
    if station and station.logo:
        try:
            if os.path.exists(station.logo.path):
                logo_flowable = Image(station.logo.path, width=42*mm, height=18*mm)
        except Exception:
            logo_flowable = None

    if not logo_flowable:
        station_initials = (station.name[:2] if station else "СТО").upper()
        logo_text = f"<b><font size=16 color='#2563eb'>[{station_initials}]</font></b><br/><font size=7 color='#64748b'>АВТОСЕРВІС</font>"
        logo_flowable = Paragraph(logo_text, st['body'])

    station_name = station.name if station else "Автосервіс"
    station_address = station.address if station else "Україна"
    station_phone = station.phone if station else ""
    station_edrpou = f" | ЄДРПОУ/ІПН: {station.edrpou}" if station and station.edrpou else ""
    station_bank = f"<br/>Р/р: {station.bank_details}" if station and station.bank_details else ""

    info_text = f"<b>{station_name}</b><br/>Адреса: {station_address}<br/>Тел: {station_phone}{station_edrpou}{station_bank}"

    header_table = Table([[logo_flowable, Paragraph(info_text, st['subtitle'])]], colWidths=[48*mm, 138*mm])
    header_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('BOTTOMPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), 0)]))
    story.append(header_table)
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceBefore=0, spaceAfter=6))

    # 2. Метадані акта
    act_num = f"ACT-{booking.pk:05d}"
    created_date_str = booking.created_at.strftime("%d.%m.%Y")
    
    title_table = Table([[Paragraph(f"АКТ ВИКОНАНИХ РОБІТ № {act_num}", st['title']), Paragraph(f"<b>Статус:</b> {booking.get_status_display()}", st['badge'])]], colWidths=[130*mm, 56*mm])
    title_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    story.append(title_table)
    story.append(Paragraph(f"від {created_date_str} р.", st['subtitle']))
    story.append(Spacer(1, 4*mm))

    # 3. Клієнт та Автомобіль
    car_info_str = f"{car.brand} {car.model} ({car.year})" if car else "—"
    vin_str = car.vin_code if car else "—"
    car_history = booking.car_history_records.first()
    mileage_str = f"{car_history.mileage:,} км".replace(',', ' ') if car_history and car_history.mileage else "Не вказано"

    details_data = [
        [Paragraph("<b>ЗАМОВНИК:</b>", st['body_bold']), Paragraph(client.full_name if client else "Клієнт", st['body']), Paragraph("<b>АВТОМОБІЛЬ:</b>", st['body_bold']), Paragraph(car_info_str, st['body'])],
        [Paragraph("<b>Телефон:</b>", st['body_bold']), Paragraph(client.phone if client else "—", st['body']), Paragraph("<b>VIN-код:</b>", st['body_bold']), Paragraph(f"<font fontName='{FONT_BOLD}'>{vin_str}</font>", st['body'])],
        [Paragraph("<b>Опис проблеми:</b>", st['body_bold']), Paragraph(booking.description or "Планове обслуговування", st['body']), Paragraph("<b>Пробіг:</b>", st['body_bold']), Paragraph(mileage_str, st['body'])],
    ]
    details_table = Table(details_data, colWidths=[28*mm, 65*mm, 28*mm, 65*mm])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#f1f5f9')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 5*mm))

    # 4. Таблиця послуг
    story.append(Paragraph("1. Виконані роботи та надані послуги", st['h2']))

    services_data = [[
        Paragraph("№", st['table_header']),
        Paragraph("Найменування робіт / послуг", st['table_header']),
        Paragraph("К-сть", st['table_header']),
        Paragraph("Ціна (грн)", st['table_header']),
        Paragraph("Сума (грн)", st['table_header']),
    ]]

    total_services_sum = Decimal('0.00')
    service_items = []
    if booking.service_name:
        service_items.append({'name': booking.service_name, 'qty': 1, 'price': car_history.price if car_history else Decimal('0.00')})

    for msg in booking.chat_messages.filter(is_approved=True, proposed_cost__gt=0):
        service_items.append({'name': msg.text or "Додаткова узгоджена робота", 'qty': 1, 'price': msg.proposed_cost})

    if not service_items and car_history and car_history.work_list:
        lines = [l.strip() for l in car_history.work_list.split('\n') if l.strip()]
        for line in lines:
            service_items.append({'name': line, 'qty': 1, 'price': car_history.price / max(len(lines), 1)})

    if not service_items:
        service_items.append({'name': "Технічне обслуговування та діагностика", 'qty': 1, 'price': car_history.price if car_history else Decimal('0.00')})

    idx = 1
    for item in service_items:
        qty, price = item['qty'], Decimal(str(item['price']))
        amount = price * qty
        total_services_sum += amount
        services_data.append([
            Paragraph(str(idx), st['table_cell']),
            Paragraph(item['name'], st['table_cell']),
            Paragraph(str(qty), st['table_cell']),
            Paragraph(f"{price:,.2f}".replace(',', ' '), st['table_cell']),
            Paragraph(f"{amount:,.2f}".replace(',', ' '), st['table_cell_bold']),
        ])
        idx += 1

    services_table = Table(services_data, colWidths=[10*mm, 106*mm, 18*mm, 26*mm, 26*mm])
    services_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    story.append(services_table)
    story.append(Spacer(1, 4*mm))

    # 5. Таблиця використаних деталей
    used_parts = booking.used_parts.all()
    total_parts_sum = Decimal('0.00')

    story.append(Paragraph("2. Використані запчастини та витратні матеріали", st['h2']))
    parts_data = [[
        Paragraph("№", st['table_header']),
        Paragraph("Найменування деталі / Артикул", st['table_header']),
        Paragraph("К-сть", st['table_header']),
        Paragraph("Ціна (грн)", st['table_header']),
        Paragraph("Сума (грн)", st['table_header']),
    ]]

    if used_parts.exists():
        idx = 1
        for up in used_parts:
            qty, price = up.quantity, up.selling_price
            amount = price * qty
            total_parts_sum += amount
            sku_str = f" [Арт: {up.spare_part.sku}]" if up.spare_part and up.spare_part.sku else ""
            parts_data.append([
                Paragraph(str(idx), st['table_cell']),
                Paragraph(f"{up.part_name}{sku_str}", st['table_cell']),
                Paragraph(f"{qty} шт", st['table_cell']),
                Paragraph(f"{price:,.2f}".replace(',', ' '), st['table_cell']),
                Paragraph(f"{amount:,.2f}".replace(',', ' '), st['table_cell_bold']),
            ])
            idx += 1
    else:
        parts_data.append([
            Paragraph("—", st['table_cell']),
            Paragraph("Запчастини та витратні матеріали не використовувалися або надані замовником", st['table_cell']),
            Paragraph("0", st['table_cell']),
            Paragraph("0.00", st['table_cell']),
            Paragraph("0.00", st['table_cell']),
        ])

    parts_table = Table(parts_data, colWidths=[10*mm, 106*mm, 18*mm, 26*mm, 26*mm])
    parts_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    story.append(parts_table)
    story.append(Spacer(1, 5*mm))

    # 6. Разом
    grand_total = total_services_sum + total_parts_sum
    if grand_total == Decimal('0.00') and car_history:
        grand_total = car_history.price

    totals_data = [
        [Paragraph("Разом за виконані роботи:", st['body']), Paragraph(f"{total_services_sum:,.2f} грн".replace(',', ' '), st['body_bold'])],
        [Paragraph("Разом за використані запчастини:", st['body']), Paragraph(f"{total_parts_sum:,.2f} грн".replace(',', ' '), st['body_bold'])],
        [Paragraph("<b>ВСЬОГО ДО СПЛАТИ:</b>", st['h2']), Paragraph(f"<b><font size=11 color='#2563eb'>{grand_total:,.2f} грн</font></b>".replace(',', ' '), st['badge'])],
    ]
    totals_table = Table(totals_data, colWidths=[130*mm, 56*mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BACKGROUND', (0, 2), (1, 2), colors.HexColor('#eff6ff')),
        ('BOX', (0, 2), (1, 2), 1, colors.HexColor('#2563eb')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 3*mm))

    words_box = Table([[Paragraph(f"<b>Сума прописом:</b> <i>{number_to_words_ua(grand_total)}</i>", st['body'])]], colWidths=[186*mm])
    words_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(words_box)
    story.append(Spacer(1, 6*mm))

    # 7. Гарантія та підписи
    terms_text = (
        "<b>Умови та гарантія:</b> Роботи виконані повністю та вчасно. Замовник претензій щодо якості та обсягу виконаних робіт не має. "
        "Гарантія на виконані роботи становить 30 днів або 2 000 км пробігу."
    )
    story.append(Paragraph(terms_text, st['subtitle']))
    story.append(Spacer(1, 8*mm))

    client_name = client.full_name if client else "Клієнт"
    signatures_data = [
        [Paragraph("<b>ВИКОНАВЕЦЬ:</b>", st['body_bold']), Paragraph("<b>ЗАМОВНИК:</b>", st['body_bold'])],
        [
            Paragraph(f"{station_name}<br/><br/>_____________________ / ___________________<br/><font size=7 color='#64748b'>(підпис / М.П.)</font>", st['body']),
            Paragraph(f"{client_name}<br/><br/>_____________________ / ___________________<br/><font size=7 color='#64748b'>(підпис)</font>", st['body']),
        ]
    ]
    signatures_table = Table(signatures_data, colWidths=[93*mm, 93*mm])
    signatures_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('TOPPADDING', (0, 0), (-1, -1), 2)]))

    story.append(KeepTogether([signatures_table]))
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()


def generate_financial_report_pdf(station, start_date, end_date, transactions, metrics, employees):
    """Генерація фінансового звіту СТО за обраний період у PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=12*mm, rightMargin=12*mm, topMargin=12*mm, bottomMargin=16*mm)
    st = get_pdf_styles()
    story = []

    logo_flowable = None
    if station and station.logo:
        try:
            if os.path.exists(station.logo.path):
                logo_flowable = Image(station.logo.path, width=40*mm, height=16*mm)
        except Exception:
            logo_flowable = None

    if not logo_flowable:
        station_initials = (station.name[:2] if station else "СТО").upper()
        logo_text = f"<b><font size=16 color='#0284c7'>[{station_initials}]</font></b><br/><font size=7 color='#64748b'>ФІНАНСОВИЙ АНАЛІЗ</font>"
        logo_flowable = Paragraph(logo_text, st['body'])

    station_name = station.name if station else "Автосервіс"
    start_str, end_str = start_date.strftime("%d.%m.%Y"), end_date.strftime("%d.%m.%Y")

    header_table = Table([[logo_flowable, Paragraph(f"<b>ФІНАНСОВИЙ ЗВІТ СТО: {station_name.upper()}</b><br/><font color='#64748b'>Період звітності: {start_str} — {end_str}</font>", st['title'])]], colWidths=[45*mm, 141*mm])
    header_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    story.append(header_table)
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284c7'), spaceBefore=0, spaceAfter=8))

    # KPI метрики
    total_income = metrics.get('total_income', Decimal('0.00'))
    total_expense = metrics.get('total_expense', Decimal('0.00'))
    net_profit = metrics.get('net_profit', Decimal('0.00'))
    profit_margin = metrics.get('profit_margin', 0.0)

    profit_color = '#16a34a' if net_profit >= 0 else '#dc2626'
    kpi_data = [
        [Paragraph("<b>ДОХІД (ГРН)</b>", st['subtitle']), Paragraph("<b>ВИРАТИ (ГРН)</b>", st['subtitle']), Paragraph("<b>ЧИСТИЙ ПРИБУТОК</b>", st['subtitle']), Paragraph("<b>РЕНТАБЕЛЬНІСТЬ</b>", st['subtitle'])],
        [
            Paragraph(f"<b><font size=12 color='#16a34a'>{total_income:,.2f}</font></b>".replace(',', ' '), st['body']),
            Paragraph(f"<b><font size=12 color='#dc2626'>{total_expense:,.2f}</font></b>".replace(',', ' '), st['body']),
            Paragraph(f"<b><font size=12 color='{profit_color}'>{net_profit:,.2f}</font></b>".replace(',', ' '), st['body']),
            Paragraph(f"<b><font size=12 color='#0284c7'>{profit_margin:.1f}%</font></b>", st['body']),
        ]
    ]

    kpi_table = Table(kpi_data, colWidths=[46.5*mm]*4)
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 6*mm))

    # Категорії
    story.append(Paragraph("1. Деталізація доходів та витрат за категоріями", st['h2']))
    inc_items = list(metrics.get('income_by_category', {}).items())
    exp_items = list(metrics.get('expense_by_category', {}).items())
    max_rows = max(len(inc_items), len(exp_items), 1)

    cat_table_data = [[Paragraph("Категорія доходу", st['table_header']), Paragraph("Сума (грн)", st['table_header']), Paragraph("Категорія витрати", st['table_header']), Paragraph("Сума (грн)", st['table_header'])]]
    for i in range(max_rows):
        inc_label, inc_val = inc_items[i] if i < len(inc_items) else ("—", Decimal('0.00'))
        exp_label, exp_val = exp_items[i] if i < len(exp_items) else ("—", Decimal('0.00'))
        cat_table_data.append([
            Paragraph(str(inc_label), st['table_cell']),
            Paragraph(f"{inc_val:,.2f}".replace(',', ' '), st['table_cell_bold']),
            Paragraph(str(exp_label), st['table_cell']),
            Paragraph(f"{exp_val:,.2f}".replace(',', ' '), st['table_cell_bold']),
        ])

    cat_table = Table(cat_table_data, colWidths=[55*mm, 38*mm, 55*mm, 38*mm])
    cat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    story.append(cat_table)
    story.append(Spacer(1, 6*mm))

    # Працівники
    if employees:
        story.append(Paragraph("2. Виробіток та зарплатний баланс працівників", st['h2']))
        emp_table_data = [[
            Paragraph("Працівник", st['table_header']), Paragraph("Посада", st['table_header']),
            Paragraph("Ставка (грн)", st['table_header']), Paragraph("Комісія %", st['table_header']),
            Paragraph("Зароблено (грн)", st['table_header']), Paragraph("Виплачено (грн)", st['table_header']),
            Paragraph("Залишок (грн)", st['table_header']),
        ]]
        for emp in employees:
            sb = getattr(emp, 'salary_balance', None)
            earned = sb.total_earned if sb else Decimal('0.00')
            paid = sb.total_paid if sb else Decimal('0.00')
            bal = sb.current_balance if sb else Decimal('0.00')
            emp_table_data.append([
                Paragraph(emp.full_name, st['table_cell_bold']), Paragraph(emp.position, st['table_cell']),
                Paragraph(f"{emp.base_salary:,.2f}".replace(',', ' '), st['table_cell']), Paragraph(f"{emp.commission_percent}%", st['table_cell']),
                Paragraph(f"{earned:,.2f}".replace(',', ' '), st['table_cell']), Paragraph(f"{paid:,.2f}".replace(',', ' '), st['table_cell']),
                Paragraph(f"{bal:,.2f}".replace(',', ' '), st['table_cell_bold']),
            ])
        emp_table = Table(emp_table_data, colWidths=[40*mm, 28*mm, 23*mm, 20*mm, 25*mm, 25*mm, 25*mm])
        emp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))
        story.append(emp_table)
        story.append(Spacer(1, 6*mm))

    # Реєстр транзакцій
    story.append(Paragraph(f"3. Реєстр фінансових операцій ({len(transactions)} записів)", st['h2']))
    tx_table_data = [[
        Paragraph("Дата", st['table_header']), Paragraph("Тип", st['table_header']),
        Paragraph("Категорія", st['table_header']), Paragraph("Опис / Деталі", st['table_header']),
        Paragraph("Сума (грн)", st['table_header']),
    ]]

    for tx in transactions[:50]:
        type_str = "Дохід" if tx.type == 'income' else "Витрата"
        type_color = '#16a34a' if tx.type == 'income' else '#dc2626'
        sign = "+" if tx.type == 'income' else "-"
        tx_table_data.append([
            Paragraph(tx.date.strftime("%d.%m.%Y"), st['table_cell']),
            Paragraph(f"<font color='{type_color}'><b>{type_str}</b></font>", st['table_cell']),
            Paragraph(tx.get_category_display(), st['table_cell']),
            Paragraph(tx.description or "—", st['table_cell']),
            Paragraph(f"<font color='{type_color}'><b>{sign}{tx.amount:,.2f}</b></font>".replace(',', ' '), st['table_cell_bold']),
        ])

    if not transactions:
        tx_table_data.append([Paragraph("—", st['table_cell']), Paragraph("—", st['table_cell']), Paragraph("—", st['table_cell']), Paragraph("Фінансових операцій не виявлено", st['table_cell']), Paragraph("0.00", st['table_cell'])])

    tx_table = Table(tx_table_data, colWidths=[22*mm, 20*mm, 44*mm, 65*mm, 35*mm])
    tx_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    story.append(tx_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()
