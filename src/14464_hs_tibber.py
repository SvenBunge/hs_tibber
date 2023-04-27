# coding: utf-8
from urllib2 import Request, urlopen, HTTPError
import json
import time
import datetime
import threading
import websocket
import uuid
import random

TIBBER_URL = 'https://api.tibber.com/v1-beta/gql'
ENERGY_PRICES_GRAPHQL = '''{
  viewer {
    websocketSubscriptionUrl
    homes {
      id
      features {
        realTimeConsumptionEnabled
      }
      currentSubscription{
        priceInfo{
          today {
            total
            startsAt
            level
          }
          tomorrow {
            total
            startsAt
            level
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

class Hs_tibber14464(hsl20_3.BaseModule):

    def __init__(self, homeserver_context):
        hsl20_3.BaseModule.__init__(self, homeserver_context, "hs_tibber14464")
        self.FRAMEWORK = self._get_framework()
        self.LOGGER = self._get_logger(hsl20_3.LOGGING_NONE,())
        self.PIN_I_API_TOKEN=1
        self.PIN_I_ENABLE_DEBUG=2
        self.PIN_I_CHEAP_PERIOD_DURATION=3
        self.PIN_I_EXPENSIVE_PERIOD_DURATION=4
        self.PIN_I_WAITTIME_BETWEEN_PERIODS=5
        self.PIN_I_AVG_THRESHOLD=6
        self.PIN_O_CURRENT_PRICE=1
        self.PIN_O_PERCENT_AVG_PRICE=2
        self.PIN_O_MIN_PRICE=3
        self.PIN_O_MAX_PRICE=4
        self.PIN_O_AVG_PRICE=5
        self.PIN_O_CHEAP_PERIOD_FIRST_HOUR=6
        self.PIN_O_CHEAP_PERIOD_AVG_PRICE=7
        self.PIN_O_CHEAP_PERIOD_NOW=8
        self.PIN_O_PRICE_JSON_TODAY=9
        self.PIN_O_PRICE_JSON_TOMORROW=10
        self.PIN_O_LIVE_AVAILABLE=11
        self.PIN_O_LIVE_POWER_CONSUMPTION=12
        self.PIN_O_LIVE_POWER_PRODUCTION=13
        self.PIN_O_LIVE_VOLTAGE_L1=14
        self.PIN_O_LIVE_VOLTAGE_L2=15
        self.PIN_O_LIVE_VOLTAGE_L3=16
        self.PIN_O_LIVE_CURRENT_L1=17
        self.PIN_O_LIVE_CURRENT_L2=18
        self.PIN_O_LIVE_CURRENT_L3=19
        self.PIN_O_LIVE_ACCUMULATED_CONSUMPTION=20
        self.PIN_O_LIVE_ACCUMULATED_COST=21
        self.PIN_O_LIVE_METER_CONSUMPTION=22
        self.PIN_O_LIVE_METER_PRODUCTION=23
        self.FRAMEWORK._run_in_context_thread(self.on_init)

########################################################################################################
#### Own written code can be placed after this commentblock . Do not change or delete commentblock! ####
###################################################################################################!!!##

        self.fetch_interval, self.calculate_outputs_interval, self.DEBUG = [None] * 3
        self.recalc_needed, self.last_hour = [None] * 2

        self.tibber_price_cache = [DUMMY_VALUE] * 48
        self.output_cache = {}
        self.live_websocket_url = None
        self.websocket_thread = None

    def on_fetch_Tibber(self):
        self.calculate_outputs_interval.start()  # restart calc timer to have the time to update price cache
        api_token = self._get_input_value(self.PIN_I_API_TOKEN)
        # time = datetime.datetime.now()
        # if api_token and (13 <= time.hour <= 17 or time.hour % 3 == 0) and self.tibber_price_cache.count(DUMMY_VALUE) > 0:
        if api_token:
            client = JsonClient(TIBBER_URL).inject_token(api_token)

            try:
                price_result = client.execute(ENERGY_PRICES_GRAPHQL)
                json_result = json.loads(price_result)

                priceinfo = json_result["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]

                ## Create new Price Cache
                self.tibber_price_cache = [DUMMY_VALUE] * 48
                self.parse_timeinfo(priceinfo['today'], 0)
                self._set_output_value(self.PIN_O_PRICE_JSON_TODAY, priceinfo['today'])
                self._set_output_value(self.PIN_O_PRICE_JSON_TOMORROW, priceinfo['tomorrow'])
                self.parse_timeinfo(priceinfo['tomorrow'], 24)
                self.log_debug("parsed_prices", str(self.tibber_price_cache))
                self.recalc_needed = True  # maybe we got an update!

                json_home = json_result["data"]["viewer"]["homes"][0]
                if json_home:  # Todo: Start thread with parser thread and not in fetch thread to reduce fetches
                    new_live_websocket_url = json_result["data"]["viewer"]["websocketSubscriptionUrl"]
                    home_id = json_home["id"]
                    live_available = bool(json_home["features"]["realTimeConsumptionEnabled"])
                    self.set_output_sbc(self.PIN_O_LIVE_AVAILABLE, live_available)
                    if new_live_websocket_url != self.live_websocket_url or not live_available:
                        if self.websocket_thread:
                            self.websocket_thread.stop()
                            self.websocket_thread = None
                        self.live_websocket_url = new_live_websocket_url  # Update URL

                    if live_available and not self.websocket_thread:  # Create new one if needed
                        self.websocket_thread = WebsocketTibberReader(new_live_websocket_url, api_token, home_id, self)
                        self.websocket_thread.run()

            except KeyError as e:
                self.log_debug("fetch error", e)
                # raise

    def parse_timeinfo(self, priceinfo_hours_of_day, start):
        if not priceinfo_hours_of_day:  # No data received. We fill with dummy values
            for idx in range(start, start + 24):
                self.tibber_price_cache[idx] = DUMMY_VALUE

        for priceinfo in priceinfo_hours_of_day:
            priceinfo_datetime_cut = str(priceinfo["startsAt"]).split('.', 2)[0]
            priceinfo_datetime = datetime.datetime.strptime(priceinfo_datetime_cut, '%Y-%m-%dT%H:%M:%S')
            self.tibber_price_cache[priceinfo_datetime.hour + start] = priceinfo["total"]

    def on_calc_outputs(self):
        self.log_debug("calculator", "started")
        if filter(lambda x: x != DUMMY_VALUE, self.tibber_price_cache) == 0:  # check if price_cache is empty and must be filled
            self.on_fetch_Tibber()

        self.log_debug("calculator", "got data")
        # recalc if pricecache is filled and we may have updates or a new hour
        now_hour = datetime.datetime.now().hour
        if now_hour != self.last_hour or self.recalc_needed:
            # rnge_today = range(now_hour, 24, 1)
            # for hour in rnge_today:
            #     self.update_hour_output(hour, self.tibber_price_cache[hour])
            #
            # if bool(self.tibber_price_cache[24]):  # Should be None if next day is not available
            #     rnge_tomorrow = range(0, now_hour, 1)
            #     for hour in rnge_tomorrow:
            #         self.update_hour_output(hour, self.tibber_price_cache[24 + hour])
            # else:  # set to fake value to signal no data
            #     rnge_tomorrow = range(0, now_hour, 1)
            #     for hour in rnge_tomorrow:
            #         self.update_hour_output(hour, DUMMY_VALUE)
            current_price = self.tibber_price_cache[now_hour]
            self.set_output_sbc(self.PIN_O_CURRENT_PRICE, current_price)
            min_price, max_price, avg_price = self.calc_price_range()
            self.set_output_sbc(self.PIN_O_MIN_PRICE, min_price)
            self.set_output_sbc(self.PIN_O_MAX_PRICE, max_price)
            self.set_output_sbc(self.PIN_O_AVG_PRICE, avg_price)
            self.set_output_sbc(self.PIN_O_PERCENT_AVG_PRICE, (current_price / avg_price - 1)*100)
            cheap_period, avg_period_price = self.calc_cheapest_period()
            self.set_output_sbc(self.PIN_O_CHEAP_PERIOD_FIRST_HOUR, cheap_period[0])
            self.set_output_sbc(self.PIN_O_CHEAP_PERIOD_AVG_PRICE, avg_period_price)
            self.set_output_sbc(self.PIN_O_CHEAP_PERIOD_NOW, now_hour in cheap_period)

    def calc_cheapest_period(self):
        # last_hour_prices = map(lambda x: self.price_dict[x]['last_price'], self.price_dict)
        period_size = self._get_input_value(self.PIN_I_CHEAP_PERIOD_DURATION)
        if period_size < 2:
            period_size = 2
        elif period_size > 6:
            period_size = 6

        avg_price = 999  # period avg
        avg_start = -1  # first hour of the cheap period
        start = datetime.datetime.now().hour
        for i in range(start, start+24):
            period = slice(i, i + period_size)
            period_prices = self.tibber_price_cache[period]
            period_prices = filter(lambda x: x is not None and x != DUMMY_VALUE, period_prices)
            if len(period_prices) != period_size:
                break
            period_avg_price = sum(period_prices) / period_size
            if avg_price > period_avg_price:
                avg_start = i
                avg_price = period_avg_price

        return map(lambda x: x % 24, range(avg_start, avg_start + period_size)), avg_price

    def calc_price_range(self):
        filtered_prices = list(filter(lambda x: x is not None and x != DUMMY_VALUE, self.tibber_price_cache))

        if len(filtered_prices) < 1:
            return DUMMY_VALUE, DUMMY_VALUE, DUMMY_VALUE
        else:
            return min(filtered_prices), max(filtered_prices), sum(filtered_prices) / len(filtered_prices)

    def set_output_sbc(self, output_num, value):
        if self.output_cache.get(output_num) != value and self._can_set_output():
            self._set_output_value(output_num, value)
            self.output_cache[output_num] = value

    def on_init(self):
        time.sleep(3)  # wait till startup is done in parallel
        self.fetch_interval = self.FRAMEWORK.create_interval()
        self.calculate_outputs_interval = self.FRAMEWORK.create_interval()
        self.fetch_interval.set_interval(3600000, self.on_fetch_Tibber)  # Every hour (skipped most of the time)
        self.calculate_outputs_interval.set_interval(30000, self.on_calc_outputs)  # Every 30s
        # self.last_hour = datetime.datetime.now().hour  # actual hour to prevent deleting the old one on first iteration
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
        return self

    def execute(self, query, variables=None):
        data = {'query': query, 'variables': variables}
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

        if self.token is not None:
            headers[self.headername] = str(self.token)

        req = Request(self.endpoint, data=json.dumps(data), headers=headers)

        try:
            return urlopen(req).read().decode('utf-8')
        except HTTPError as e:
            print(e.read())
            raise e

class WebsocketTibberReader(threading.Thread):

    def __init__(self, websocket_url, token, home_id, parent):
        threading.Thread.__init__(self)
        self.data_id = None
        self.parent = parent
        self.token = token
        self.home_id = home_id
        self.reconnect_wait_seconds = 0
        self.values = {"power": parent.PIN_O_LIVE_POWER_CONSUMPTION,
                       "powerProduction": parent.PIN_O_LIVE_POWER_PRODUCTION,
                       "voltagePhase1": parent.PIN_O_LIVE_VOLTAGE_L1,
                       "voltagePhase2": parent.PIN_O_LIVE_VOLTAGE_L2,
                       "voltagePhase3": parent.PIN_O_LIVE_VOLTAGE_L3,
                       "currentL1": parent.PIN_O_LIVE_CURRENT_L1,
                       "currentL2": parent.PIN_O_LIVE_CURRENT_L2,
                       "currentL3": parent.PIN_O_LIVE_CURRENT_L3,
                       "accumulatedConsumption": parent.PIN_O_LIVE_ACCUMULATED_CONSUMPTION,
                       "accumulatedCost": parent.PIN_O_LIVE_ACCUMULATED_COST,
                       "lastMeterConsumption": parent.PIN_O_LIVE_METER_CONSUMPTION,
                       "lastMeterProduction": parent.PIN_O_LIVE_METER_PRODUCTION
                       }
        self.ws = websocket.WebSocketApp(websocket_url, on_open=self.onconn, on_message=self.onmsg, on_close=self.onclose,
                                         on_error=self.onerror,
                                    header={'User-Agent': 'Gira HomeServer LBS by Sven Bunge Spike'},
                                    subprotocols=["graphql-transport-ws"])

    def onconn(self, ws):
        ws.send('{"type":"connection_init","payload":{"token":"' + self.token + '"}}')
        self.parent.log_debug("WS state", "sent auth")

    def onmsg(self, ws, msg):
        self.parent.log_debug("WSS data", msg)

        jsnbody = json.loads(msg)
        tpe = jsnbody['type']
        if tpe and tpe == "connection_ack":
            self.parent.log_debug("WS state", "authenticated")
            data_id = uuid.uuid4()

            reqKeys = " ".join(self.values.keys())
            reqStr = '{"id":"' + str(data_id) + '","type":"subscribe","payload":{"variables":{},"extensions":{},"query":"subscription {\\n  liveMeasurement(homeId: \\"' + self.home_id + '\\") {' + reqKeys + '}}"}}'
            ws.send(reqStr)
            self.parent.log_debug("WS state", "data requested")
        elif tpe and tpe == "next":
            livedata = jsnbody['payload']['data']['liveMeasurement']
            for key in self.values.keys():
                self.parent.set_output_sbc(self.values[key], livedata[key])
            self.parent.log_debug("WS state", "running: " + str(datetime.datetime.now()))

        self.reconnect_wait_seconds = 0  # Setup reconnect threshold back to 0

    def onclose(self, ws):
        # We stop the thread and wait till its restarted on next tibber fetch (with maybe updated fetch WS-path)
        self.parent.log_debug("WS state", "closed")
        # Slow down reconnect
        randint = random.randint(5, 60)
        self.reconnect_wait_seconds = self.reconnect_wait_seconds * 2 + randint
        if self.reconnect_wait_seconds > 1440:
            self.stop()
        else:
            time.sleep(self.reconnect_wait_seconds)

    def onerror(self, ws, err):
        now = datetime.datetime.now()
        self.parent.log_debug("WS error " + str(now), str(err))
        self.stop()

    def stop(self):
        self.ws.run_forever = False  # Will shutdown the client soon

    def run(self):
        self.ws.run_forever(suppress_origin=True, ping_interval=30, ping_timeout=5)
