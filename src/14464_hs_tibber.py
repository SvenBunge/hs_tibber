# coding: utf-8
import json
import time
import datetime
import threading
import websocket
import uuid
import random
import hsl2helper

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

        self.fetch_interval, self.update, self.last_hour = [None] * 3
        self.help = hsl2helper.HSL2Helper(self)
        self.tibber_price_cache = [None] * 48
        self.live_websocket_url = None
        self.live_available = False
        self.home_id = None
        self.websocket_thread = None
        self.last_fetch = None

    def update_tibber_price_info(self):
        self.help.log_msg("fetching: started")
        api_token = self._get_input_value(self.PIN_I_API_TOKEN)
        if api_token:
            client = self.help.new_json_client(TIBBER_URL).inject_auth_token("Bearer " + api_token)

            try:
                json_result = client.execute({'query': ENERGY_PRICES_GRAPHQL, 'variables': None})
                self.help.log_msg("fetching: got json")

                priceinfo = json_result["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]

                # Create new Price Cache
                self.tibber_price_cache = [None] * 48
                self.parse_timeinfo(priceinfo['today'], 0)
                self.parse_timeinfo(priceinfo['tomorrow'], 24)
                self.help.set_output_sbc(self.PIN_O_PRICE_JSON_TODAY, priceinfo['today'])\
                    .set_output_sbc(self.PIN_O_PRICE_JSON_TOMORROW, priceinfo['tomorrow'])
                self.help.log_msg("fetching: prices parsed:" + str(self.tibber_price_cache))

                json_home = json_result["data"]["viewer"]["homes"][0]
                if json_home:
                    new_live_websocket_url = json_result["data"]["viewer"]["websocketSubscriptionUrl"]
                    self.home_id = json_home["id"]
                    self.live_available = bool(json_home["features"]["realTimeConsumptionEnabled"])
                    self.help.set_output_sbc(self.PIN_O_LIVE_AVAILABLE, self.live_available)
                    if new_live_websocket_url != self.live_websocket_url or not self.live_available:
                        if self.websocket_thread:
                            self.help.log_msg("fetching: stopped WS thread because URL changed or live data unavail.")
                            self.websocket_thread.stop()
                            self.websocket_thread = None
                        self.live_websocket_url = new_live_websocket_url  # Update URL

                    self.restart_tibber_live_thread()

            except Exception:
                self.help.log_err("on fetch tibber failed")

    def restart_tibber_live_thread(self):
        """
        creates the tibber live thread or restarts it if live should be available and thread is dead.
        """
        if self.live_available and self.live_websocket_url and\
                (not self.websocket_thread or self.websocket_thread.is_alive()):
            self.help.log_msg("fetching: (re)starting WS thread (live data)")
            api_token = self._get_input_value(self.PIN_I_API_TOKEN)
            self.websocket_thread = WebsocketTibberReader(self.live_websocket_url, api_token, self.home_id, self)
            self.websocket_thread.start()
            self.help.log_msg("fetching: started WS thread")

    def parse_timeinfo(self, priceinfo_hours_of_day, start):
        if not priceinfo_hours_of_day:  # No data received. We fill with dummy values
            for idx in range(start, start + 24):
                self.tibber_price_cache[idx] = None

        for priceinfo in priceinfo_hours_of_day:
            priceinfo_datetime_cut = str(priceinfo["startsAt"]).split('.', 2)[0]
            priceinfo_datetime = datetime.datetime.strptime(priceinfo_datetime_cut, '%Y-%m-%dT%H:%M:%S')
            self.tibber_price_cache[priceinfo_datetime.hour + start] = priceinfo["total"]

    def on_calc_outputs(self):
        try:
            self.help.log_msg("calculator: started")
            if filter(lambda x: x, self.tibber_price_cache) == 0:  # skip if empty price list
                pass

            self.help.log_msg("calculator: got data")
            # recalc if price cache is filled and we may have updates or a new hour
            now_hour = datetime.datetime.now().hour
            if now_hour != self.last_hour:
                current_price = self.tibber_price_cache[now_hour]
                self.help.set_output_sbc(self.PIN_O_CURRENT_PRICE, current_price)
                min_price, max_price, avg_price = self.calc_price_range()
                self.help.set_output_sbc(self.PIN_O_MIN_PRICE, min_price)\
                    .set_output_sbc(self.PIN_O_MAX_PRICE, max_price)\
                    .set_output_sbc(self.PIN_O_AVG_PRICE, avg_price)\
                    .set_output_sbc(self.PIN_O_PERCENT_AVG_PRICE, (current_price / avg_price - 1)*100)
                cheap_period, avg_period_price = self.calc_cheapest_period()
                self.help.set_output_sbc(self.PIN_O_CHEAP_PERIOD_FIRST_HOUR, cheap_period[0])\
                    .set_output_sbc(self.PIN_O_CHEAP_PERIOD_AVG_PRICE, avg_period_price)\
                    .set_output_sbc(self.PIN_O_CHEAP_PERIOD_NOW, now_hour in cheap_period)
                self.last_hour = now_hour
            self.help.log_msg("calculator: finished")

            self.restart_tibber_live_thread()
        except Exception:
            self.help.log_err("on price calc output failed")

    def calc_cheapest_period(self):
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
            period_prices = filter(lambda x: x is not None, period_prices)
            if len(period_prices) != period_size:
                break
            period_avg_price = sum(period_prices) / period_size
            if avg_price > period_avg_price:
                avg_start = i
                avg_price = period_avg_price

        return map(lambda x: x % 24, range(avg_start, avg_start + period_size)), avg_price

    def calc_price_range(self):
        filtered_prices = list(filter(lambda x: x is not None, self.tibber_price_cache))

        if len(filtered_prices) < 1:
            return DUMMY_VALUE, DUMMY_VALUE, DUMMY_VALUE
        else:
            return min(filtered_prices), max(filtered_prices), sum(filtered_prices) / len(filtered_prices)

    def on_update(self):
        # Update tibber every hour
        now = datetime.datetime.now()
        if self.last_fetch is None or (now - self.last_fetch).total_seconds() > 3600:
            self.update_tibber_price_info()
            self.last_fetch = now

        # extract values
        self.on_calc_outputs()

    def on_init(self):
        time.sleep(3)  # wait till startup is done in parallel
        self.update = self.FRAMEWORK.create_interval()
        self.update.set_interval(60000, self.on_update)  # Every 60s
        self.update.start()
        time.sleep(3)
        self.on_update()  # Start faster!

    def on_input_value(self, index, value):
        if self.PIN_I_API_TOKEN == index:  # Restart timer
            self.update_tibber_price_info()  # fetch immediately

class WebsocketTibberReader(threading.Thread):

    def __init__(self, websocket_url, token, home_id, parent):
        threading.Thread.__init__(self)
        self.help = parent.help
        self.data_id = None
        self.parent = parent
        self.token = token
        self.home_id = home_id
        self.last_data_recv_time = 0
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
        self.help.log_debug("WS state", "sent auth")

    def onmsg(self, ws, msg):
        self.help.log_debug("WS data", msg)

        jsnbody = json.loads(msg)
        tpe = jsnbody['type']
        if tpe and tpe == "connection_ack":
            self.help.log_debug("WS state", "authenticated")
            data_id = uuid.uuid4()

            reqKeys = " ".join(self.values.keys())
            reqStr = '{"id":"' + str(data_id) + '","type":"subscribe","payload":{"variables":{},"extensions":{},"query":"subscription {\\n  liveMeasurement(homeId: \\"' + self.home_id + '\\") {' + reqKeys + '}}"}}'
            ws.send(reqStr)
            self.help.log_debug("WS state", "data requested")
        elif tpe and tpe == "next":
            livedata = jsnbody['payload']['data']['liveMeasurement']
            for key in self.values.keys():
                self.help.set_output_sbc(self.values[key], livedata[key])
            self.last_data_recv_time = datetime.datetime.now()
            self.help.log_debug("WS state", "running: " + str(self.last_data_recv_time))
        else:
            self.help.log_debug("WS state", "got crazy shit: " + str(tpe))

    def onclose(self, ws):
        # We stop the thread and wait till its restarted on next tibber fetch (with maybe updated fetch WS-path)
        self.help.log_debug("WS state", "closed")
        self.stop()

    def onerror(self, ws, err):
        now = datetime.datetime.now()
        self.help.log_debug("WS error " + str(now), str(err))
        self.stop()

    def is_alive(self):
        self.isAlive() and self.ws.keep_running

    def stop(self):
        if self.ws.keep_running:
            self.ws.keep_running = False  # Will shutdown the client soon

    def run(self):
        self.help.log_msg("WS thread: Started run thread")
        # The next command stalls till the WS closes. That's ok, the update-calculation timer is starting it clean again
        self.ws.run_forever(suppress_origin=True, ping_interval=30, ping_timeout=5)
        # WS died, let's end this wrapping thread.
        self.stop()
        self.help.log_msg("WS thread: End run thread")
