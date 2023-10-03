import unittest
import json
from pricecalc import PriceLine, Prices, TibberPriceIndicator


class PriceCalcTest(unittest.TestCase):

    def test_should_find_max_value(self):
        today = PriceCalcTest.createDayArray(0.2461, 0.244, 0.2443, 0.2426, 0.247, 0.2513,
                                                  0.2819, 0.3039, 0.3051, 0.2855, 0.2585, 0.2432,
                                                  0.2406, 0.2378, 0.2381, 0.2408, 0.2593, 0.2917,
                                                  0.3711, 0.4247, 0.3236, 0.2759, 0.2605, 0.2521)
        prices = Prices()
        prices.set_today(today)
        self.assertEqual(0.4247, prices.get_today_max())  # add assertion here

    def test_should_find_min_value(self):
        today = PriceCalcTest.createDayArray(0.2461, 0.244, 0.2443, 0.2426, 0.247, 0.2513,
                                                  0.2819, 0.3039, 0.3051, 0.2855, 0.2585, 0.2432,
                                                  0.2406, 0.2378, 0.2381, 0.2408, 0.2593, 0.2917,
                                                  0.3711, 0.4247, 0.3236, 0.2759, 0.2605, 0.2521)
        prices = Prices()
        prices.set_today(today)
        self.assertEqual(0.2378, prices.get_today_min())  # add assertion here

    def test_should_calc_avg_value(self):
        today = PriceCalcTest.createDayArray(0.2461, 0.244, 0.2443, 0.2426, 0.247, 0.2513,
                                                  0.2819, 0.3039, 0.3051, 0.2855, 0.2585, 0.2432,
                                                  0.2406, 0.2378, 0.2381, 0.2408, 0.2593, 0.2917,
                                                  0.3711, 0.4247, 0.3236, 0.2759, 0.2605, 0.2521)
        prices = Prices()
        prices.set_today(today)
        self.assertEqual(0.274, prices.get_today_avg())  # add assertion here

    def test_should_calc_percentage_to_average_smaller(self):
        today = PriceCalcTest.createDayArray(0.2461, 0.244, 0.2443, 0.2426, 0.247, 0.2513,
                                                  0.2819, 0.3039, 0.3051, 0.2855, 0.2585, 0.2432,
                                                  0.2406, 0.2378, 0.2381, 0.2408, 0.2593, 0.2917,
                                                  0.3711, 0.4247, 0.3236, 0.2759, 0.2605, 0.2521)
        prices = Prices()
        prices.set_today(today)
        self.assertEqual(-10.182, prices.get_price_to_avg_percentage(0))  # add assertion here

    def test_should_calc_percentage_to_average_bigger(self):
        today = PriceCalcTest.createDayArray(0.2461, 0.244, 0.2443, 0.2426, 0.247, 0.2513,
                                                  0.2819, 0.3039, 0.3051, 0.2855, 0.2585, 0.2432,
                                                  0.2406, 0.2378, 0.2381, 0.2408, 0.2593, 0.2917,
                                                  0.3711, 0.4247, 0.3236, 0.2759, 0.2605, 0.2521)
        prices = Prices()
        prices.set_today(today)
        self.assertEqual(55.0, prices.get_price_to_avg_percentage(19))  # add assertion here


    def test_today_parsing(self):
        today_json = """
        [
                                {
                                    "total": 0.2461,
                                    "startsAt": "2023-10-02T00:00:00.000+02:00",
                                    "level": "NORMAL"
                                },
                                {
                                    "total": 0.244,
                                    "startsAt": "2023-10-02T01:00:00.000+02:00",
                                    "level": "NORMAL"
                                },
                                {
                                    "total": 0.2443,
                                    "startsAt": "2023-10-02T02:00:00.000+02:00",
                                    "level": "NORMAL"
                                },
                                {
                                    "total": 0.2426,
                                    "startsAt": "2023-10-02T03:00:00.000+02:00",
                                    "level": "NORMAL"
                                },
                                {
                                    "total": 0.247,
                                    "startsAt": "2023-10-02T04:00:00.000+02:00",
                                    "level": "NORMAL"
                                },
                                {
                                    "total": 0.2513,
                                    "startsAt": "2023-10-02T05:00:00.000+02:00",
                                    "level": "NORMAL"
                                },
                                {
                                    "total": 0.2819,
                                    "startsAt": "2023-10-02T06:00:00.000+02:00",
                                    "level": "EXPENSIVE"
                                },
                                {
                                    "total": 0.3039,
                                    "startsAt": "2023-10-02T07:00:00.000+02:00",
                                    "level": "EXPENSIVE"
                                },
                                {
                                    "total": 0.3051,
                                    "startsAt": "2023-10-02T08:00:00.000+02:00",
                                    "level": "EXPENSIVE"
                                },
                                {
                                    "total": 0.2855,
                                    "startsAt": "2023-10-02T09:00:00.000+02:00",
                                    "level": "EXPENSIVE"
                                },
                                {
                                    "total": 0.2585,
                                    "startsAt": "2023-10-02T10:00:00.000+02:00",
                                    "level": "NORMAL"
                                },
                                {
                                    "total": 0.2432,
                                    "startsAt": "2023-10-02T11:00:00.000+02:00",
                                    "level": "NORMAL"
                                },
                                {
                                    "total": 0.2406,
                                    "startsAt": "2023-10-02T12:00:00.000+02:00",
                                    "level": "NORMAL"
                                },
                                {
                                    "total": 0.2378,
                                    "startsAt": "2023-10-02T13:00:00.000+02:00",
                                    "level": "NORMAL"
                                },
                                {
                                    "total": 0.2381,
                                    "startsAt": "2023-10-02T14:00:00.000+02:00",
                                    "level": "NORMAL"
                                },
                                {
                                    "total": 0.2408,
                                    "startsAt": "2023-10-02T15:00:00.000+02:00",
                                    "level": "NORMAL"
                                },
                                {
                                    "total": 0.2593,
                                    "startsAt": "2023-10-02T16:00:00.000+02:00",
                                    "level": "NORMAL"
                                },
                                {
                                    "total": 0.2917,
                                    "startsAt": "2023-10-02T17:00:00.000+02:00",
                                    "level": "EXPENSIVE"
                                },
                                {
                                    "total": 0.3711,
                                    "startsAt": "2023-10-02T18:00:00.000+02:00",
                                    "level": "VERY_EXPENSIVE"
                                },
                                {
                                    "total": 0.4247,
                                    "startsAt": "2023-10-02T19:00:00.000+02:00",
                                    "level": "VERY_EXPENSIVE"
                                },
                                {
                                    "total": 0.3236,
                                    "startsAt": "2023-10-02T20:00:00.000+02:00",
                                    "level": "EXPENSIVE"
                                },
                                {
                                    "total": 0.2759,
                                    "startsAt": "2023-10-02T21:00:00.000+02:00",
                                    "level": "NORMAL"
                                },
                                {
                                    "total": 0.2605,
                                    "startsAt": "2023-10-02T22:00:00.000+02:00",
                                    "level": "NORMAL"
                                },
                                {
                                    "total": 0.2521,
                                    "startsAt": "2023-10-02T23:00:00.000+02:00",
                                    "level": "NORMAL"
                                }
                            ]
        """
        today = json.loads(today_json)
        prices = Prices()
        prices.parse_today(today)
        self.assertEqual(float('0.2521'), prices.get_todays_price(23))
        self.assertEqual(TibberPriceIndicator.NORMAL, prices.get_todays_priceindicator(23))

    @staticmethod
    def createDayArray(*args):
        if not 23 <= len(args) <= 25:
            raise "didn't get 23-25 prices a day!"
        i = 0;
        pricelist = []
        for price in args:
            pricelist.append(PriceLine(i, price, "NORMAL"))
            i += 1

        return pricelist


if __name__ == '__main__':
    unittest.main()
