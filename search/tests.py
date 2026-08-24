from unittest import mock

from django.core.management import call_command
from django.db import OperationalError
from django.test import TestCase
from django.urls import reverse

from main.models import Review, Service, ServiceStation, User
from main.textnorm import escape_like, fold_text, tokenize
from search import views as search_views


class TextNormTests(TestCase):
    def test_fold_text_lowercases_cyrillic_and_collapses_whitespace(self):
        self.assertEqual(fold_text('  КИЇВ   столиця '), 'київ столиця')

    def test_fold_text_maps_yo_to_ye(self):
        self.assertEqual(fold_text('ЁЖИК ёлка'), 'ежик елка')

    def test_fold_text_unifies_apostrophes(self):
        base = fold_text("слов'янськ")
        self.assertEqual(base, fold_text('слов\u2019янськ'))
        self.assertEqual(base, fold_text('слов\u02bcянськ'))
        self.assertEqual(base, fold_text('слов`янськ'))

    def test_tokenize_splits_by_any_whitespace(self):
        self.assertEqual(tokenize('  Заміна\tмасла\nфільтра '), ['заміна', 'масла', 'фільтра'])

    def test_escape_like_escapes_wildcards_and_backslash(self):
        self.assertEqual(escape_like('a%b_c\\d'), 'a\\%b\\_c\\\\d')


class SearchTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create(
            full_name='Власник СТО',
            phone='+380671112233',
            email='owner@test.com',
            role='station',
        )
        self.near_station = ServiceStation.objects.create(
            name='Близьке СТО',
            address='Хрещатик, 1',
            city='Київ',
            phone='+380671110011',
            user=self.owner,
            latitude='50.451100',
            longitude='30.523400',
        )
        self.kyiv_no_coords_station = ServiceStation.objects.create(
            name='Безкоординатне СТО',
            address='Вулиця Тестова, 2',
            city='Київ',
            phone='+380671110033',
            user=self.owner,
        )
        self.far_station = ServiceStation.objects.create(
            name='Далеке СТО',
            address='Вулиця Ірпінська, 55',
            city='Київ',
            phone='+380671110022',
            user=self.owner,
            latitude='50.320000',
            longitude='30.450000',
        )
        self.lviv_station = ServiceStation.objects.create(
            name='Львівське СТО',
            address='Площа Ринок, 1',
            city='Львів',
            phone='+380671110044',
            user=self.owner,
            latitude='49.839700',
            longitude='24.029700',
        )
        self.apostrophe_station = ServiceStation.objects.create(
            name="Слов'янськ Авто",
            address='Вулиця Центральна, 3',
            city="Слов'янськ",
            phone='+380671110055',
            user=self.owner,
        )
        self.oil_service = Service.objects.create(
            service_name='Заміна масла і фільтра',
            price='500.00',
            station=self.near_station,
        )
        self.diag_service = Service.objects.create(
            service_name='Діагностика двигуна',
            price='400.00',
            station=self.near_station,
        )
        self.tires_service = Service.objects.create(
            service_name='Шиномонтаж',
            price='300.00',
            station=self.lviv_station,
        )
        self.yo_service = Service.objects.create(
            service_name='Регенерация ёмкости АКБ',
            price='900.00',
            station=self.kyiv_no_coords_station,
        )
        Review.objects.create(text='Чудово', rating=5, user=self.owner, station=self.near_station)
        Review.objects.create(text='Добре', rating=4, user=self.owner, station=self.near_station)
        Review.objects.create(text='Нормально', rating=3, user=self.owner, station=self.lviv_station)

    def search(self, **params):
        return self.client.get(reverse('search:search_stations'), params)

    def shown_ids(self, response):
        return {item['station'].pk for item in response.context['station_data']}

    def test_search_page_loads(self):
        response = self.search()
        self.assertEqual(response.status_code, 200)

    def test_post_method_not_allowed(self):
        response = self.client.post(reverse('search:search_stations'), {'city': 'Київ'})
        self.assertEqual(response.status_code, 405)

    def test_search_with_radius_filter(self):
        response = self.search(lat='50.4501', lng='30.5234', radius='10')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_radius'], 10)
        shown = self.shown_ids(response)
        self.assertIn(self.near_station.pk, shown)
        self.assertNotIn(self.far_station.pk, shown)
        self.assertNotIn(self.kyiv_no_coords_station.pk, shown)

    def test_radius_without_coordinates_is_ignored(self):
        response = self.search(radius='10')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], ServiceStation.objects.count())

    def test_city_search_case_insensitive_for_cyrillic_lowercase(self):
        response = self.search(city='київ')
        self.assertEqual(response.context['total_count'], 3)
        self.assertIn(self.near_station.pk, self.shown_ids(response))

    def test_city_search_with_extra_spaces_and_mixed_case(self):
        response = self.search(city='  КИЇВ  ')
        self.assertEqual(response.context['total_count'], 3)

    def test_city_search_matches_apostrophe_variants(self):
        response = self.search(city='слов\u2019янськ')
        self.assertIn(self.apostrophe_station.pk, self.shown_ids(response))
        response = self.search(city="слов'ян")
        self.assertIn(self.apostrophe_station.pk, self.shown_ids(response))

    def test_service_search_tokens_match_in_any_order(self):
        response = self.search(service='масла заміна')
        self.assertIn(self.near_station.pk, self.shown_ids(response))

    def test_service_search_requires_all_tokens(self):
        response = self.search(service='заміна фільтра')
        self.assertIn(self.near_station.pk, self.shown_ids(response))
        response = self.search(service='заміна шиномонтаж')
        self.assertEqual(response.context['total_count'], 0)

    def test_service_search_folded_prefix_and_partial_match(self):
        response = self.search(service='масл')
        self.assertIn(self.near_station.pk, self.shown_ids(response))
        response = self.search(service='ёмкости')
        self.assertIn(self.kyiv_no_coords_station.pk, self.shown_ids(response))
        response = self.search(service='емкости')
        self.assertIn(self.kyiv_no_coords_station.pk, self.shown_ids(response))

    def test_percent_sign_treated_as_literal_not_wildcard(self):
        response = self.search(city='%')
        self.assertEqual(response.context['total_count'], 0)
        response = self.search(city='Ки%')
        self.assertEqual(response.context['total_count'], 0)

    def test_underscore_treated_as_literal_not_wildcard(self):
        response = self.search(city='Ки_в')
        self.assertEqual(response.context['total_count'], 0)

    def test_sql_like_input_treated_literally_and_harmless(self):
        payload = "'; DROP TABLE user; --"
        response = self.search(city=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 0)
        self.assertEqual(ServiceStation.objects.count(), 5)

    def test_emoji_input_returns_empty_result_without_error(self):
        response = self.search(city='\U0001F697\U0001F680')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 0)

    def test_very_long_input_does_not_break_query(self):
        response = self.search(city='а' * 5000)
        self.assertEqual(response.status_code, 200)

    def test_empty_and_whitespace_only_filters_return_everything(self):
        response = self.search(city='   ', service='\n\t ', rating='')
        self.assertEqual(response.context['total_count'], ServiceStation.objects.count())

    def test_rating_filter_includes_only_matching_average(self):
        response = self.search(rating='4')
        shown = self.shown_ids(response)
        self.assertIn(self.near_station.pk, shown)
        self.assertNotIn(self.lviv_station.pk, shown)
        self.assertNotIn(self.kyiv_no_coords_station.pk, shown)

    def test_rating_filter_accepts_comma_decimal(self):
        response = self.search(rating='4,5')
        self.assertIn(self.near_station.pk, self.shown_ids(response))
        self.assertNotIn(self.lviv_station.pk, self.shown_ids(response))

    def test_invalid_rating_values_are_ignored(self):
        total = ServiceStation.objects.count()
        for bad in ('abc', '-1', '99', '', '0'):
            response = self.search(rating=bad)
            self.assertEqual(response.context['total_count'], total, msg=f'rating={bad!r}')

    def test_nan_and_inf_coordinates_are_rejected(self):
        total = ServiceStation.objects.count()
        response = self.search(lat='NaN', lng='inf')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], total)
        self.assertIsNone(response.context['user_lat'])
        response = self.search(lat='-inf', lng='30.5')
        self.assertIsNone(response.context['user_lat'])

    def test_out_of_range_coordinates_are_rejected(self):
        total = ServiceStation.objects.count()
        response = self.search(lat='95', lng='30.52')
        self.assertEqual(response.context['total_count'], total)
        response = self.search(lat='50.45', lng='-200')
        self.assertEqual(response.context['total_count'], total)
        response = self.search(lat='50.45', lng='30.52', radius='99999')
        self.assertEqual(response.context['total_count'], total)

    def test_results_sorted_by_distance_then_pk(self):
        west = ServiceStation.objects.create(
            name='Західне СТО',
            address='А, 1',
            city='Київ',
            phone='+380671110066',
            user=self.owner,
            latitude='50.450000',
            longitude='30.520000',
        )
        east = ServiceStation.objects.create(
            name='Східне СТО',
            address='Б, 2',
            city='Київ',
            phone='+380671110077',
            user=self.owner,
            latitude='50.450000',
            longitude='30.540000',
        )
        response = self.search(lat='50.450000', lng='30.530000')
        data = response.context['station_data']
        measured = [item['distance_km'] for item in data if item['distance_km'] is not None]
        self.assertEqual(measured, sorted(measured))
        pks = [item['station'].pk for item in data]
        self.assertLess(pks.index(west.pk), pks.index(east.pk))
        self.assertEqual(pks[0], self.near_station.pk)

    def test_stations_without_distance_sorted_after_measured_ones(self):
        response = self.search(lat='50.4501', lng='30.5234')
        data = response.context['station_data']
        measured = [item['distance_km'] for item in data if item['distance_km'] is not None]
        unmeasured = [item for item in data if item['distance_km'] is None]
        self.assertTrue(measured)
        self.assertTrue(unmeasured)
        pks = [item['station'].pk for item in data]
        tail_pks = {item['station'].pk for item in unmeasured}
        self.assertEqual(set(pks[len(measured):]), tail_pks)


class SearchPaginationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create(
            full_name='Власник СТО',
            phone='+380671112233',
            email='owner@test.com',
            role='station',
        )
        for i in range(search_views.PAGE_SIZE + 5):
            station = ServiceStation.objects.create(
                name=f'СТО Пагінація {i:02d}',
                address='Адреса',
                city='Київ',
                phone='+380671200000',
                user=self.owner,
            )
            Review.objects.create(text='Ок', rating=5, user=self.owner, station=station)

    def search(self, **params):
        return self.client.get(reverse('search:search_stations'), params)

    def test_first_page_limited_and_total_counts_all(self):
        response = self.search(city='київ')
        self.assertEqual(len(response.context['station_data']), search_views.PAGE_SIZE)
        self.assertEqual(response.context['total_count'], search_views.PAGE_SIZE + 5)

    def test_second_page_contains_remainder(self):
        response = self.search(city='київ', page='2')
        self.assertEqual(len(response.context['station_data']), 5)
        self.assertEqual(response.context['page_obj'].number, 2)

    def test_page_beyond_range_clamped_to_last(self):
        response = self.search(city='київ', page='999')
        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertEqual(len(response.context['station_data']), 5)

    def test_invalid_page_falls_back_to_first(self):
        response = self.search(city='київ', page='abc')
        self.assertEqual(response.context['page_obj'].number, 1)
        response = self.search(city='київ', page='-3')
        self.assertEqual(response.context['page_obj'].number, 1)

    def test_pagination_links_preserve_other_params(self):
        response = self.search(city='київ', rating='4', page='2')
        html = response.content.decode('utf-8')
        self.assertIn('city=%D0%BA%D0%B8%D1%97%D0%B2', html)
        self.assertIn('rating=4', html)
        self.assertIn('page=1', html)


class SearchSuggestTests(TestCase):
    def setUp(self):
        owner = User.objects.create(
            full_name='Власник СТО',
            phone='+380671112233',
            email='owner@test.com',
            role='station',
        )
        station = ServiceStation.objects.create(
            name='СТО',
            address='Хрещатик, 1',
            city='Київ',
            phone='+380671110011',
            user=owner,
        )
        Service.objects.create(service_name='Заміна масла', price='500.00', station=station)

    def test_suggest_cities_cyrillic_case_insensitive(self):
        response = self.client.get(reverse('search:search_suggest'), {'q': 'ки'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['cities'], ['Київ'])

    def test_suggest_services_folded(self):
        response = self.client.get(reverse('search:search_suggest'), {'q': 'ЗАМІНА МАС'})
        self.assertEqual(response.json()['services'], ['Заміна масла'])
        response = self.client.get(reverse('search:search_suggest'), {'q': 'замена'})
        self.assertEqual(response.json()['services'], [])

    def test_suggest_empty_query_returns_empty_lists(self):
        response = self.client.get(reverse('search:search_suggest'), {'q': '   '})
        self.assertEqual(response.json(), {'query': '', 'cities': [], 'services': []})

    def test_suggest_wildcards_return_nothing(self):
        response = self.client.get(reverse('search:search_suggest'), {'q': '%'})
        self.assertEqual(response.json()['cities'], [])
        response = self.client.get(reverse('search:search_suggest'), {'q': 'К_'})
        self.assertEqual(response.json()['cities'], [])

    def test_suggest_limit_is_clamped(self):
        response = self.client.get(reverse('search:search_suggest'), {'q': 'ки', 'limit': '9999'})
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('search:search_suggest'), {'q': 'ки', 'limit': 'abc'})
        self.assertEqual(response.status_code, 200)


class SearchDbFailureTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create(
            full_name='Власник СТО',
            phone='+380671112233',
            email='owner@test.com',
            role='station',
        )

    def test_database_error_rendered_as_empty_state(self):
        class FailingManager:
            def annotate(self, *args, **kwargs):
                raise OperationalError('db down')

        class FailingStation:
            objects = FailingManager()

        with mock.patch.object(search_views, 'ServiceStation', FailingStation):
            response = self.client.get(reverse('search:search_stations'), {'city': 'київ'})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['db_error'])
        self.assertEqual(list(response.context['station_data']), [])
        self.assertEqual(response.context['total_count'], 0)


class RebuildSearchNormsCommandTests(TestCase):
    def test_command_restores_norm_fields_after_raw_update(self):
        owner = User.objects.create(
            full_name='Власник СТО',
            phone='+380671112233',
            email='owner@test.com',
            role='station',
        )
        station = ServiceStation.objects.create(
            name='СТО',
            address='А',
            city='Київ',
            phone='+380671110011',
            user=owner,
        )
        service = Service.objects.create(service_name='Діагностика', price='100.00', station=station)

        ServiceStation.objects.all().update(name_norm='', city_norm='')
        Service.objects.all().update(service_name_norm='')

        call_command('rebuild_search_norms', verbosity=0)

        station.refresh_from_db()
        service.refresh_from_db()
        self.assertEqual(station.city_norm, 'київ')
        self.assertEqual(station.name_norm, 'сто')
        self.assertEqual(service.service_name_norm, 'діагностика')

        response = self.client.get(reverse('search:search_stations'), {'city': 'КИЇВ'})
        self.assertEqual(response.context['total_count'], 1)
