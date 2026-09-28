import datetime
import logging
import re

import requests


logger = logging.getLogger(__name__)

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

YEAR_CODES = 'ABCDEFGHJKLMNPRSTVWXY123456789'


def _parse_year_fallback(vin):
    try:
        index = YEAR_CODES.index(vin[9])
    except ValueError:
        return None

    first_year = 1980 + index
    latest_year = datetime.date.today().year + 1

    possible_years = [
        first_year + 30 * cycle
        for cycle in range(3)
        if first_year + 30 * cycle <= latest_year
    ]
    return max(possible_years) if possible_years else None


def _local_result(vin):
    brand_info = WMI_MAP.get(vin[:3])

    return {
        'status': 'success',
        'vin': vin,
        'brand': brand_info[0] if brand_info else 'Невідомий бренд',
        'model': '',
        'year': _parse_year_fallback(vin),
        'engine': '',
        'fuel_type': '',
        'body_class': '',
        'source': 'pattern',
    }


def decode_vin(vin_code):
    vin = str(vin_code or '').strip().upper()

    if not vin:
        return {'status': 'error', 'message': 'VIN-код порожній'}

    if not re.fullmatch(r'[A-HJ-NPR-Z0-9]{17}', vin):
        return {
            'status': 'error',
            'message': 'VIN має містити 17 символів без літер I, O та Q',
        }

    url = f'https://vpic.nhtsa.dot.gov/api/vehicles/decodevinvalues/{vin}'

    try:
        response = requests.get(
            url,
            params={'format': 'json'},
            timeout=(2, 4),
        )
        response.raise_for_status()
        results = response.json().get('Results', [])

        if results:
            item = results[0]
            make = (item.get('Make') or '').strip()
            model = (item.get('Model') or '').strip()

            if make and model:
                brand_info = WMI_MAP.get(vin[:3])
                if brand_info and brand_info[0].upper() == make.upper():
                    brand = brand_info[0]
                elif make.isupper():
                    brand = make.title()
                else:
                    brand = make

                year_text = str(item.get('ModelYear') or '').strip()
                year = (
                    int(year_text)
                    if year_text.isdigit()
                    else _parse_year_fallback(vin)
                )

                displacement = (item.get('DisplacementL') or '').strip()
                cylinders = (item.get('EngineCylinders') or '').strip()
                fuel_type = (item.get('FuelTypePrimary') or '').strip()
                engine = f'{displacement}L' if displacement else ''

                if engine and cylinders:
                    engine += f', {cylinders} цил.'

                return {
                    'status': 'success',
                    'vin': vin,
                    'brand': brand,
                    'model': model,
                    'year': year,
                    'engine': engine,
                    'fuel_type': fuel_type,
                    'body_class': (item.get('BodyClass') or '').strip(),
                    'source': 'nhtsa',
                }
    except (requests.RequestException, ValueError, TypeError, KeyError) as error:
        logger.warning('Не вдалося декодувати VIN через NHTSA: %s', error)

    return _local_result(vin)
