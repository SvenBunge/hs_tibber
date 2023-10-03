import datetime
import decimal
from decimal import Decimal
from enum34 import Enum

class PriceLine:

    def __init__(self, hour, price, tibber_price_indicator):
        self.hour = hour
        self.price = price
        self.priceindicator = tibber_price_indicator # See TibberPriceIndicator-Enum: "VERY_CHEAP", "CHEAP", "NORMAL", "EXPENSIVE", "VERY_EXPENSIVE"

    def get_hour(self):
        return self.hour

    def get_price(self):
        return self.price

    def get_price_indicator(self):
        return self.priceindicator

    def __str__(self):
        return str(self.hour) + "::" + str(self.price) + "::" + self.priceindicator

    def __repr__(self):
        return self.__str__()


class Prices:

    def __init__(self):
        self.prices_today = [None] * 24
        self.prices_tomorrow = [None] * 24

    def get_today_prices(self):
        return self.prices_today

    def get_todays_price(self, hour):
        if self.prices_today is not None:
            return self.prices_today[hour].get_price()

    def get_todays_priceindicator(self, hour):
        if self.prices_today is not None:
            return self.prices_today[hour].get_price_indicator()

    def get_today_avg(self):
        if self.prices_today is not None:
            prices = list(map(lambda p: p.price, self.prices_today))
            avg = sum(prices) / len(prices)
            return self.trunc_float(avg, 3)

    def trunc_float(self, value, digits):
        decimal_desc = '0.'
        for i in range(0, digits):
            decimal_desc = decimal_desc + '0'
        return float(Decimal(value).quantize(Decimal(decimal_desc), rounding=decimal.ROUND_HALF_UP))

    def get_price_to_avg_percentage(self, hour):
        if self.prices_today is not None:
            percentage_to_avg = (self.get_todays_price(hour) / self.get_today_avg() - 1) * 100
            return self.trunc_float(percentage_to_avg, 3)

    def get_today_min(self):
        if self.prices_today is not None:
            prices = map(lambda p: p.price, self.prices_today)
            return min(prices)

    def get_today_max(self):
        if self.prices_today is not None:
            prices = map(lambda p: p.price, self.prices_today)
            return max(prices)

    def get_tomorrow_prices(self):
        return self.prices_tomorrow

    def set_today(self, priceinfo):
        """Helper function for tests"""
        self.prices_today = priceinfo

    def set_tomorrow(self, priceinfo):
        """Helper function for tests"""
        self.prices_tomorrow = priceinfo

    def parse_today(self, priceinfo_hours_of_day):
        self.prices_today = self.parse_timeinfo(priceinfo_hours_of_day)

    def parse_tomorrow(self, priceinfo_hours_of_day):
        self.prices_tomorrow = self.parse_timeinfo(priceinfo_hours_of_day)

    def parse_timeinfo(self, priceinfo_hours_of_day):
        if not priceinfo_hours_of_day:  # No data received. We fill with dummy values
            return None

        prices = []
        for priceinfo in priceinfo_hours_of_day:
            priceinfo_datetime_cut = str(priceinfo["startsAt"]).split('.', 2)[0]
            priceinfo_datetime = datetime.datetime.strptime(priceinfo_datetime_cut, '%Y-%m-%dT%H:%M:%S')
            # Todo: Work with timezone to prevent hazzle on summer time changeover
            price_indicator = TibberPriceIndicator.from_str(priceinfo["level"])
            prices.append(PriceLine(priceinfo_datetime.hour, priceinfo["total"], price_indicator))

        return prices

    def check_day_rollover(self, now_hour):
        """day change. should be called on every calc-cycle. If called with hour 0, it uses tomorrow values for today"""
        if now_hour == 0 and self.prices_tomorrow is not None:
            self.prices_today = self.prices_tomorrow
            self.prices_tomorrow = None

class TibberPriceIndicator(Enum):
    VERY_CHEAP = -2
    CHEAP = -1
    NORMAL = 0
    EXPENSIVE = 1
    VERY_EXPENSIVE = 2

    @staticmethod
    def from_str(value):
        for t in TibberPriceIndicator:
            if t.name == value:
                return t
