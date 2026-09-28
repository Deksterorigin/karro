import re


SUPPLIERS = [
    {'code': 'intercars', 'name': 'InterCars Україна', 'badge_color': '#0284c7'},
    {'code': 'exist', 'name': 'Exist.ua', 'badge_color': '#16a34a'},
    {'code': 'technovector', 'name': 'TechnoVector / Омега', 'badge_color': '#d97706'},
]

CATALOG_DATABASE = [
    {
        'sku': 'P 85 020',
        'oem': '8E0 698 151 F',
        'part_name': 'Гальмівні колодки передні',
        'brand': 'Brembo',
        'category': 'Гальмівна система',
        'supplier_code': 'intercars',
        'supplier_name': 'InterCars Україна',
        'cost_price': 1250.00,
        'suggested_retail_price': 1750.00,
        'stock_qty': 14,
        'delivery_days': 0,
        'compatibility': 'VAG (Audi A4, A6, Passat B6/B7)',
    },
    {
        'sku': '0 986 479 098',
        'oem': '5Q0 615 301 A',
        'part_name': 'Гальмівний диск вентильований',
        'brand': 'BOSCH',
        'category': 'Гальмівна система',
        'supplier_code': 'exist',
        'supplier_name': 'Exist.ua',
        'cost_price': 1680.00,
        'suggested_retail_price': 2250.00,
        'stock_qty': 8,
        'delivery_days': 1,
        'compatibility': 'VW Golf VII, Octavia A7, Passat B8',
    },
    {
        'sku': 'GDB1330',
        'oem': '1J0 698 151 D',
        'part_name': 'Колодки гальмівні передні TRW',
        'brand': 'TRW',
        'category': 'Гальмівна система',
        'supplier_code': 'technovector',
        'supplier_name': 'TechnoVector / Омега',
        'cost_price': 980.00,
        'suggested_retail_price': 1350.00,
        'stock_qty': 22,
        'delivery_days': 0,
        'compatibility': 'Skoda Octavia Tour, VW Golf IV',
    },
    {
        'sku': 'HU 719/7 x',
        'oem': '071 115 562 C',
        'part_name': 'Фільтр масляний картридж',
        'brand': 'MANN-FILTER',
        'category': 'Фільтри',
        'supplier_code': 'intercars',
        'supplier_name': 'InterCars Україна',
        'cost_price': 240.00,
        'suggested_retail_price': 380.00,
        'stock_qty': 45,
        'delivery_days': 0,
        'compatibility': 'VAG 1.9 TDI, 2.0 TDI',
    },
    {
        'sku': 'C 30 005',
        'oem': '5Q0 129 620 B',
        'part_name': 'Фільтр повітряний двигуна',
        'brand': 'MANN-FILTER',
        'category': 'Фільтри',
        'supplier_code': 'exist',
        'supplier_name': 'Exist.ua',
        'cost_price': 390.00,
        'suggested_retail_price': 580.00,
        'stock_qty': 30,
        'delivery_days': 0,
        'compatibility': 'Skoda Kodiaq, Tiguan, Octavia',
    },
    {
        'sku': 'MOT-8100-5W30-5L',
        'oem': 'MOTUL-8100-XCLEAN',
        'part_name': 'Олива моторна Motul 8100 X-clean EFE 5W-30 (5L)',
        'brand': 'Motul',
        'category': 'Автохімія та оливи',
        'supplier_code': 'technovector',
        'supplier_name': 'TechnoVector / Омега',
        'cost_price': 1650.00,
        'suggested_retail_price': 2200.00,
        'stock_qty': 18,
        'delivery_days': 0,
        'compatibility': 'Універсальна (ACEA C2/C3, MB 229.52, BMW LL-04)',
    },
    {
        'sku': 'CAS-EDGE-5W30-4L',
        'oem': 'CASTROL-EDGE-LL',
        'part_name': 'Олива моторна Castrol EDGE Titanium LL 5W-30 (4L)',
        'brand': 'Castrol',
        'category': 'Автохімія та оливи',
        'supplier_code': 'intercars',
        'supplier_name': 'InterCars Україна',
        'cost_price': 1480.00,
        'suggested_retail_price': 1950.00,
        'stock_qty': 25,
        'delivery_days': 0,
        'compatibility': 'VW 504.00 / 507.00',
    },
    {
        'sku': '31925 01',
        'oem': '1K0 407 151 AC',
        'part_name': 'Важіль підвіски передній лівий/правий',
        'brand': 'Lemförder',
        'category': 'Ходова частина',
        'supplier_code': 'exist',
        'supplier_name': 'Exist.ua',
        'cost_price': 2100.00,
        'suggested_retail_price': 2850.00,
        'stock_qty': 10,
        'delivery_days': 1,
        'compatibility': 'VW Passat B6/B7, CC, Tiguan',
    },
    {
        'sku': '311 409',
        'oem': '3C0 513 025 E',
        'part_name': 'Амортизатор задній газомасляний Sachs',
        'brand': 'Sachs',
        'category': 'Ходова частина',
        'supplier_code': 'intercars',
        'supplier_name': 'InterCars Україна',
        'cost_price': 1850.00,
        'suggested_retail_price': 2490.00,
        'stock_qty': 12,
        'delivery_days': 0,
        'compatibility': 'Passat B6/B7, Superb II',
    },
    {
        'sku': 'VLINE-28',
        'oem': '101 000 063 AA',
        'part_name': 'Свічка запалювання NGK BKR6E-11',
        'brand': 'NGK',
        'category': 'Запалювання',
        'supplier_code': 'technovector',
        'supplier_name': 'TechnoVector / Омега',
        'cost_price': 140.00,
        'suggested_retail_price': 210.00,
        'stock_qty': 120,
        'delivery_days': 0,
        'compatibility': 'Японські та європейські авто 1.6-2.0L',
    },
    {
        'sku': 'K015607XS',
        'oem': '03L 198 119 F',
        'part_name': 'Комплект ременя ГРМ з помпою Gates',
        'brand': 'Gates',
        'category': 'Двигун та ГРМ',
        'supplier_code': 'intercars',
        'supplier_name': 'InterCars Україна',
        'cost_price': 3450.00,
        'suggested_retail_price': 4600.00,
        'stock_qty': 6,
        'delivery_days': 1,
        'compatibility': 'VAG 1.6 / 2.0 TDI Common Rail',
    },
    {
        'sku': '5416XS',
        'oem': '06A 109 119 C',
        'part_name': 'Ремінь ГРМ Gates PowerGrip',
        'brand': 'Gates',
        'category': 'Двигун та ГРМ',
        'supplier_code': 'exist',
        'supplier_name': 'Exist.ua',
        'cost_price': 620.00,
        'suggested_retail_price': 890.00,
        'stock_qty': 15,
        'delivery_days': 0,
        'compatibility': 'Audi A4 1.6/1.8T, Golf IV 1.6',
    },
]


def search_supplier_parts(query='', supplier_code='all'):
    query_text = str(query).strip().casefold()
    query_compact = re.sub(r'[\s\-/\.]', '', query_text)
    results = []

    for part in CATALOG_DATABASE:
        if supplier_code not in ('', 'all', None, part['supplier_code']):
            continue

        searchable = ' '.join(
            str(part[field])
            for field in (
                'sku',
                'oem',
                'part_name',
                'brand',
                'category',
                'compatibility',
            )
        ).casefold()

        compact = re.sub(r'[\s\-/\.]', '', searchable)
        if not query_text or query_text in searchable or query_compact in compact:
            results.append(part)

    return {
        'status': 'success',
        'query': query,
        'count': len(results),
        'suppliers': SUPPLIERS,
        'parts': results,
    }
