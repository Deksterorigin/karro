import re
import requests
import logging

logger = logging.getLogger(__name__)

# Словник WMI для швидкого визначення маркувальних даних автівки за першими символами
WMI_MAP = {
    'WBA': ('BMW', 'Німеччина'),
    'WBS': ('BMW M', 'Німеччина'),
    'WAU': ('Audi', 'Німеччина'),
    'WVW': ('Volkswagen', 'Німеччина'),
    'WV1': ('Volkswagen Commercial', 'Німеччина'),
    'WDD': ('Mercedes-Benz', 'Німеччина'),
    'WDB': ('Mercedes-Benz', 'Німеччина'),
    'WP0': ('Porsche', 'Німеччина'),
    'W0L': ('Opel', 'Німеччина'),
    'VF1': ('Renault', 'Франція'),
    'VF3': ('Peugeot', 'Франція'),
    'VF7': ('Citroën', 'Франція'),
    'TMB': ('Škoda', 'Чехія'),
    'ZFA': ('Fiat', 'Італія'),
    'ZAR': ('Alfa Romeo', 'Італія'),
    'SAL': ('Land Rover', 'Великобританія'),
    'SCC': ('Lotus', 'Великобританія'),
    'YV1': ('Volvo', 'Швеція'),
    '1FA': ('Ford', 'США'),
    '1FT': ('Ford Truck', 'США'),
    '1FM': ('Ford SUV', 'США'),
    '1G1': ('Chevrolet', 'США'),
    '1G6': ('Cadillac', 'США'),
    '1J4': ('Jeep', 'США'),
    '2G1': ('Chevrolet', 'Канада'),
    '3FA': ('Ford', 'Мексика'),
    '5YJ': ('Tesla', 'США'),
    'JTE': ('Toyota', 'Японія'),
    'JT2': ('Toyota', 'Японія'),
    'JTD': ('Toyota', 'Японія'),
    'JN1': ('Nissan', 'Японія'),
    'JM1': ('Mazda', 'Японія'),
    'JS1': ('Suzuki', 'Японія'),
    'JH4': ('Acura', 'Японія'),
    'JHM': ('Honda', 'Японія'),
    'JA3': ('Mitsubishi', 'Японія'),
    'KMH': ('Hyundai', 'Південна Корея'),
    'KNA': ('Kia', 'Південна Корея'),
    'KL1': ('Chevrolet (Daewoo)', 'Південна Корея'),
    'SJN': ('Nissan', 'Великобританія'),
    'UU1': ('Dacia', 'Румунія'),
}

# 10-й символ VIN визначає рік випуску (SAE J272)
YEAR_CODES = {
    'A': 2010, 'B': 2011, 'C': 2012, 'D': 2013, 'E': 2014,
    'F': 2015, 'G': 2016, 'H': 2017, 'J': 2018, 'K': 2019,
    'L': 2020, 'M': 2021, 'N': 2022, 'P': 2023, 'R': 2024,
    'S': 2025, 'T': 2026, '1': 2001, '2': 2002, '3': 2003,
    '4': 2004, '5': 2005, '6': 2006, '7': 2007, '8': 2008, '9': 2009
}

def decode_vin(vin_code):
    if not vin_code:
        return {'status': 'error', 'message': 'VIN-код порожній'}

    clean_vin = re.sub(r'[^A-HJ-NPR-Z0-9]', '', str(vin_code).strip().upper())
    if len(clean_vin) != 17:
        return {'status': 'error', 'message': 'VIN-код має містити рівно 17 символів'}

    # Запит до NHTSA API
    nhtsa_url = f'https://vpic.nhtsa.dot.gov/api/vehicles/decodevinvalues/{clean_vin}?format=json'
    try:
        resp = requests.get(nhtsa_url, timeout=3.5)
        if resp.status_code == 200:
            results = resp.json().get('Results', [])
            if results:
                item = results[0]
                make = item.get('Make', '').strip()
                model = item.get('Model', '').strip()
                year_str = item.get('ModelYear', '').strip()
                displacement = item.get('DisplacementL', '').strip()
                cylinders = item.get('EngineCylinders', '').strip()
                fuel_type = item.get('FuelTypePrimary', '').strip()
                body_class = item.get('BodyClass', '').strip()

                if make and model:
                    engine_desc = ""
                    if displacement:
                        engine_desc = f"{displacement}L"
                        if cylinders:
                            engine_desc += f" V{cylinders}" if cylinders in ['6', '8', '12'] else f" i{cylinders}"
                    elif fuel_type:
                        engine_desc = fuel_type

                    year_val = int(year_str) if year_str.isdigit() else _parse_year_fallback(clean_vin)

                    return {
                        'status': 'success',
                        'vin': clean_vin,
                        'brand': make.capitalize(),
                        'model': model,
                        'year': year_val,
                        'engine': engine_desc or 'Бензин',
                        'fuel_type': fuel_type,
                        'body_class': body_class,
                        'source': 'nhtsa'
                    }
    except Exception as err:
        logger.warning(f"Помилка отримання даних через NHTSA API ({clean_vin}): {err}")

    # Локальний фолбек за WMI кодом
    wmi = clean_vin[:3]
    brand_info = WMI_MAP.get(wmi)
    
    if not brand_info:
        for k, v in WMI_MAP.items():
            if clean_vin.startswith(k[:2]):
                brand_info = v
                break

    brand_name = brand_info[0] if brand_info else 'Невідомий бренд'
    year_val = _parse_year_fallback(clean_vin)

    return {
        'status': 'success',
        'vin': clean_vin,
        'brand': brand_name,
        'model': 'Модель',
        'year': year_val,
        'engine': '2.0L Бензин',
        'fuel_type': 'Бензин',
        'body_class': 'Легковий',
        'source': 'pattern'
    }

def _parse_year_fallback(vin):
    return YEAR_CODES.get(vin[9], 2018)

