# coding: utf-8
import ssl
from urllib2 import Request, urlopen, HTTPError
import json
import time
import datetime
import numpy as np

TIBBER_URL = 'https://api.tibber.com/v1-beta/gql'
ENERGY_PRICES_GRAPHQL = '''{
  viewer {
    homes {
      currentSubscription{
        priceInfo{
          today {
            total
            startsAt
          }
          tomorrow {
            total
            startsAt
          }
        }
      }
    }
  }
}'''
DUMMY_VALUE = -999

##!!!!##################################################################################################
#### Own written code can be placed above this commentblock . Do not change or delete commentblock! ####
########################################################################################################
##** Code created by generator - DO NOT CHANGE! **##

class Hs_tibberprices14464(hsl20_3.BaseModule):

    def __init__(self, homeserver_context):
        hsl20_3.BaseModule.__init__(self, homeserver_context, "hs_tibberprices14464")
        self.FRAMEWORK = self._get_framework()
        self.LOGGER = self._get_logger(hsl20_3.LOGGING_NONE,())
        self.PIN_I_API_TOKEN=1
        self.PIN_I_ENABLE_DEBUG=2
        self.PIN_I_CHEAP_PERIOD_DURATION=3
        self.PIN_O_CURRENT_PRICE=1
        self.PIN_O_PERCENT_AVG_PRICE=2
        self.PIN_O_MIN_PRICE=3
        self.PIN_O_MAX_PRICE=4
        self.PIN_O_AVG_PRICE=5
        self.PIN_O_CHEAP_PERIOD_FIRST_HOUR=6
        self.PIN_O_CHEAP_PERIOD_LAST_HOUR=7
        self.PIN_O_CHEAP_PERIOD_AVG_PRICE=8
        self.PIN_O_CHEAP_PERIOD_NOW=9
        self.PIN_O_PRICE_0=10
        self.PIN_O_PRICE_1=11
        self.PIN_O_PRICE_2=12
        self.PIN_O_PRICE_3=13
        self.PIN_O_PRICE_4=14
        self.PIN_O_PRICE_5=15
        self.PIN_O_PRICE_6=16
        self.PIN_O_PRICE_7=17
        self.PIN_O_PRICE_8=18
        self.PIN_O_PRICE_9=19
        self.PIN_O_PRICE_10=20
        self.PIN_O_PRICE_11=21
        self.PIN_O_PRICE_12=22
        self.PIN_O_PRICE_13=23
        self.PIN_O_PRICE_14=24
        self.PIN_O_PRICE_15=25
        self.PIN_O_PRICE_16=26
        self.PIN_O_PRICE_17=27
        self.PIN_O_PRICE_18=28
        self.PIN_O_PRICE_19=29
        self.PIN_O_PRICE_20=30
        self.PIN_O_PRICE_21=31
        self.PIN_O_PRICE_22=32
        self.PIN_O_PRICE_23=33
        self.FRAMEWORK._run_in_context_thread(self.on_init)

########################################################################################################
#### Own written code can be placed after this commentblock . Do not change or delete commentblock! ####
###################################################################################################!!!##

        self.fetch_interval, self.calculate_outputs_interval, self.DEBUG = [None] * 3
        self.recalc_needed, self.last_hour = [None] * 2
        
        self.price_dict = {
            0: {"last_price": None, "output": self.PIN_O_PRICE_0},
            1: {"last_price": None, "output": self.PIN_O_PRICE_1},
            2: {"last_price": None, "output": self.PIN_O_PRICE_2},
            3: {"last_price": None, "output": self.PIN_O_PRICE_3},
            4: {"last_price": None, "output": self.PIN_O_PRICE_4},
            5: {"last_price": None, "output": self.PIN_O_PRICE_5},
            6: {"last_price": None, "output": self.PIN_O_PRICE_6},
            7: {"last_price": None, "output": self.PIN_O_PRICE_7},
            8: {"last_price": None, "output": self.PIN_O_PRICE_8},
            9: {"last_price": None, "output": self.PIN_O_PRICE_9},
            10: {"last_price": None, "output": self.PIN_O_PRICE_10},
            11: {"last_price": None, "output": self.PIN_O_PRICE_11},
            12: {"last_price": None, "output": self.PIN_O_PRICE_12},
            13: {"last_price": None, "output": self.PIN_O_PRICE_13},
            14: {"last_price": None, "output": self.PIN_O_PRICE_14},
            15: {"last_price": None, "output": self.PIN_O_PRICE_15},
            16: {"last_price": None, "output": self.PIN_O_PRICE_16},
            17: {"last_price": None, "output": self.PIN_O_PRICE_17},
            18: {"last_price": None, "output": self.PIN_O_PRICE_18},
            19: {"last_price": None, "output": self.PIN_O_PRICE_19},
            20: {"last_price": None, "output": self.PIN_O_PRICE_20},
            21: {"last_price": None, "output": self.PIN_O_PRICE_21},
            22: {"last_price": None, "output": self.PIN_O_PRICE_22},
            23: {"last_price": None, "output": self.PIN_O_PRICE_23}
        }
        self.tibber_price_cache = [None] * 48
        self.output_cache = {}

    def on_fetch_Tibber(self):
        self.calculate_outputs_interval.start()  # restart calc timer to have 15s where we can update the price cache

        api_token = self._get_input_value(self.PIN_I_API_TOKEN)
        if api_token:
            client = JsonClient(TIBBER_URL)
            client.inject_token(api_token)

            try:
                price_result = client.execute(ENERGY_PRICES_GRAPHQL)
                json_result = json.loads(price_result)

                priceinfo = json_result["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]

                ## Create new Price Cache
                self.tibber_price_cache = [None] * 48
                self.parse_timeinfo(priceinfo['today'], 0)
                self.parse_timeinfo(priceinfo['tomorrow'], 24)
                self.log_debug("parsed_prices", str(self.tibber_price_cache))
                self.recalc_needed = True  # maybe we got an update!
            except KeyError as e:
                self.log_debug("fetch error", e)
                # raise

    def parse_timeinfo(self, priceinfo_hours_of_day, start):
        if not priceinfo_hours_of_day:
            for idx in range(start, start + 24):
                self.tibber_price_cache[idx] = DUMMY_VALUE

        for priceinfo in priceinfo_hours_of_day:
            priceinfo_datetime_cut = str(priceinfo["startsAt"]).split('.', 2)[0]
            priceinfo_datetime = datetime.datetime.strptime(priceinfo_datetime_cut, '%Y-%m-%dT%H:%M:%S')
            self.tibber_price_cache[priceinfo_datetime.hour + start] = priceinfo["total"]

    def on_calc_outputs(self):
        if not bool(filter(lambda x: bool(x), self.tibber_price_cache)):  # check if price_cache is empty and must be filled
            self.on_fetch_Tibber()

        # recalc if pricecache is filled and we may have updates or a new hour
        now_hour = datetime.datetime.now().hour
        if bool(filter(lambda x: bool(x), self.tibber_price_cache)) and (now_hour != self.last_hour or self.recalc_needed):
            rnge_today = range(now_hour, 24, 1)
            for hour in rnge_today:
                self.update_hour_output(hour, self.tibber_price_cache[hour])

            if bool(self.tibber_price_cache[24]):  # Should be None if next day is not available
                rnge_tomorrow = range(0, now_hour, 1)
                for hour in rnge_tomorrow:
                    self.update_hour_output(hour, self.tibber_price_cache[24 + hour])
            else:  # set to fake value to signal no data
                rnge_tomorrow = range(0, now_hour, 1)
                for hour in rnge_tomorrow:
                    self.update_hour_output(hour, DUMMY_VALUE)

            current_price = self.price_dict[now_hour]['last_price']
            self._set_output_value(self.PIN_O_CURRENT_PRICE, current_price)
            min_price, max_price, avg_price = self.calc_price_range()
            self.set_output_sbc(self.PIN_O_MIN_PRICE, min_price)
            self.set_output_sbc(self.PIN_O_MAX_PRICE, max_price)
            self.set_output_sbc(self.PIN_O_AVG_PRICE, avg_price)
            self.set_output_sbc(self.PIN_O_PERCENT_AVG_PRICE, current_price / avg_price)
            cheap_period, avg_period_price = self.calc_cheapest_period()
            self.set_output_sbc(self.PIN_O_CHEAP_PERIOD_FIRST_HOUR, cheap_period[0])
            self.set_output_sbc(self.PIN_O_CHEAP_PERIOD_LAST_HOUR, cheap_period[-1] % 24)
            self.set_output_sbc(self.PIN_O_CHEAP_PERIOD_AVG_PRICE, avg_period_price)
            self.set_output_sbc(self.PIN_O_CHEAP_PERIOD_NOW, now_hour in cheap_period)

    def calc_cheapest_period(self):
        # last_hour_prices = map(lambda x: self.price_dict[x]['last_price'], self.price_dict)
        period_size = self._get_input_value(self.PIN_I_CHEAP_PERIOD_DURATION)
        avg_price = 999  # period avg
        avg_start = -1  # first hour of the cheap period
        start = datetime.datetime.now().hour
        for i in range(start, start+24):
            period = slice(i, i + period_size)
            period_prices = self.tibber_price_cache[period]
            if len(period_prices) != period_size:
                break
            period_avg_price = sum(period_prices) / period_size
            if avg_price > period_avg_price:
                avg_start = i
                avg_price = period_avg_price

        return map(lambda x: x % 24, range(avg_start, avg_start + period_size)), avg_price

    def calc_price_range(self):
        last_hour_prices = map(lambda x: self.price_dict[x]['last_price'], self.price_dict)
        filtered_prices = filter(lambda x: x is not None and x != DUMMY_VALUE, last_hour_prices)

        return min(filtered_prices), max(filtered_prices), sum(filtered_prices) / len(filtered_prices)

    def update_hour_output(self, hour, value):
        last_price = self.price_dict[hour]['last_price']
        if last_price != value:
            self.price_dict[hour]['last_price'] = value
            self._set_output_value(self.price_dict[hour]['output'], value)

    def set_output_sbc(self, output_num, value):
        if self.output_cache.get(output_num) != value:
            self._set_output_value(output_num, value)
            self.output_cache[output_num] = value

    def on_init(self):
        time.sleep(2)  # wait till startup is done in parallel
        self.fetch_interval = self.FRAMEWORK.create_interval()
        self.calculate_outputs_interval = self.FRAMEWORK.create_interval()
        self.calculate_outputs_interval.set_interval(3600000, self.on_fetch_Tibber)  # Every hour
        self.fetch_interval.set_interval(30000, self.on_calc_outputs)  # Every 30s
        self.last_hour = datetime.datetime.now().hour  # actual hour to prevent deleting the old one on first iteration
        self.on_input_value(self.PIN_I_API_TOKEN, self._get_input_value(self.PIN_I_API_TOKEN))

    def on_input_value(self, index, value):
        if index == self.PIN_I_API_TOKEN:  # Restart timer
            self.fetch_interval.start()
            self.calculate_outputs_interval.start()
            self.on_fetch_Tibber()  # fetch immediately

    def log_debug(self, key, value):
        if bool(self._get_input_value(self.PIN_I_ENABLE_DEBUG)):
            if not self.DEBUG:
                self.DEBUG = self.FRAMEWORK.create_debug_section()

            self.DEBUG.set_value(str(key), str(value))


class JsonClient:
    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.token = None
        self.headername = None

    def inject_token(self, token, headername='Authorization'):
        self.token = token
        self.headername = headername

    def execute(self, query, variables=None):
        data = {'query': query,
                'variables': variables}
        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json'}

        if self.token is not None:
            headers[self.headername] = str(self.token)

        req = Request(self.endpoint, data=json.dumps(data), headers=headers)

        try:
            ctx = ssl._create_unverified_context()
            response = urlopen(req, context=ctx)
            return response.read().decode('utf-8')
        except HTTPError as e:
            print(e.read())
            raise e
