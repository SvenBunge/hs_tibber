# coding: utf-8
import json
import time
import datetime
import threading
import websocket
import uuid
import hsl2helper
import pricecalc

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
        self.PIN_O_CURRENT_PRICE=1
        self.PIN_O_PERCENT_AVG_PRICE=2
        self.PIN_O_CURRENT_1D_PRICE_LEVEL=3
        self.PIN_O_CURRENT_3D_PRICE_LEVEL=4
        self.PIN_O_MIN_PRICE=5
        self.PIN_O_MAX_PRICE=6
        self.PIN_O_AVG_PRICE=7
        self.PIN_O_PRICE_JSON_TODAY=8
        self.PIN_O_PRICE_JSON_TOMORROW=9
        self.PIN_O_LIVE_AVAILABLE=10
        self.PIN_O_LIVE_POWER=11
        self.PIN_O_LIVE_VOLTAGE_L1=12
        self.PIN_O_LIVE_VOLTAGE_L2=13
        self.PIN_O_LIVE_VOLTAGE_L3=14
        self.PIN_O_LIVE_CURRENT_L1=15
        self.PIN_O_LIVE_CURRENT_L2=16
        self.PIN_O_LIVE_CURRENT_L3=17
        self.PIN_O_LIVE_ACCUMULATED_CONSUMPTION=18
        self.PIN_O_LIVE_ACCUMULATED_COST=19
        self.PIN_O_LIVE_METER_CONSUMPTION=20
        self.PIN_O_LIVE_METER_FEEDIN=21
        self.FRAMEWORK._run_in_context_thread(self.on_init)

########################################################################################################
#### Own written code can be placed after this commentblock . Do not change or delete commentblock! ####
###################################################################################################!!!##

        self.fetch_interval, self.update = [None] * 2
        self.help = hsl2helper.HSL2Helper(self)
        self.price = pricecalc.Prices()
        self.live_websocket_url = None
        self.live_available = False
        self.home_id = None
        self.websocket_thread = None
        self.last_fetch = None

    def update_tibber_price_info(self):
        self.help.log_msg("fetching: started")
        api_token = self.help.get_input(self.PIN_I_API_TOKEN)
        if api_token:
            client = self.help.new_json_client(TIBBER_URL).inject_auth_token("Bearer " + api_token)

            try:
                json_result = client.execute({'query': ENERGY_PRICES_GRAPHQL, 'variables': None})
                self.help.log_msg("fetching: got json")

                priceinfo = json_result["data"]["viewer"]["homes"][0]["currentSubscription"]["priceInfo"]

                # Create new Price Cache
                self.price.parse_today(priceinfo['today'])
                self.price.parse_tomorrow(priceinfo['tomorrow'])
                self.help.set_output_sbc(self.PIN_O_PRICE_JSON_TODAY, priceinfo['today'])\
                    .set_output_sbc(self.PIN_O_PRICE_JSON_TOMORROW, priceinfo['tomorrow'])

                # Creates websocket live connection for energy meter (live) data
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
        # If thread is running but data is gone or url has changed, stop it!
        if self.websocket_thread and self.websocket_thread.is_alive() and \
                (not self.live_available or self.live_websocket_url != self.websocket_thread.websocket_url):
            self.websocket_thread.stop()

        # Start the thread if live data should be there
        if self.live_available and self.live_websocket_url and\
                (not self.websocket_thread or not self.websocket_thread.is_alive()):
            self.help.log_msg("fetching: (re)starting WS thread (live data)")
            if self.websocket_thread: # just doublecheck that the thread is stopping before we discard the reference
                self.websocket_thread.stop()
            api_token = self.help.get_input(self.PIN_I_API_TOKEN)
            self.websocket_thread = WebsocketTibberReader(self.live_websocket_url, api_token, self.home_id, self)
            self.websocket_thread.start()
            self.help.log_msg("fetching: started WS thread")

    def on_calc_outputs(self):
        try:
            self.help.log_msg("calculator: started")
            if self.price.get_today_prices() is None:
                pass

            self.help.log_msg("calculator: got data")
            # recalc if price cache is filled and we may have updates or a new hour
            now_hour = datetime.datetime.now().hour
            self.price.check_day_rollover(now_hour)
            self.help.set_output_sbc(self.PIN_O_CURRENT_PRICE, self.price.get_todays_price(now_hour))

            # AVG-Stuff
            (self.help.set_output_sbc(self.PIN_O_PERCENT_AVG_PRICE, self.price.get_price_to_avg_percentage(now_hour))
             .set_output_sbc(self.PIN_O_CURRENT_1D_PRICE_LEVEL, self.price.get_todays_price_1dlevel(now_hour).value)
             .set_output_sbc(self.PIN_O_CURRENT_3D_PRICE_LEVEL, self.price.get_todays_price_3dlevel(now_hour).value))

            # Day values
            (self.help.set_output_sbc(self.PIN_O_MIN_PRICE, self.price.get_today_min())
             .set_output_sbc(self.PIN_O_AVG_PRICE, self.price.get_today_avg())
             .set_output_sbc(self.PIN_O_MAX_PRICE, self.price.get_today_max()))

            self.restart_tibber_live_thread()
        except Exception:
            self.help.log_err("on price calc output failed")
        finally:
            self.help.log_msg("calculator: finished")

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
    """
    Websocket watcher go get the live values from a tibber pulse like device.
    Not used for any kind of pricing but for getting all numbers from the power meter.
    Its running in a dedicated thread - and I guess the websocket is also running in a second. It's writing
    it's values directy to the outputs.
    """
    def __init__(self, websocket_url, token, home_id, parent):
        threading.Thread.__init__(self)
        self.help = parent.help
        self.data_id = None
        self.parent = parent
        self.token = token
        self.home_id = home_id
        self.last_data_recv_time = 0
        self.websocket_url = websocket_url
        self.values = {"power": parent.PIN_O_LIVE_POWER,
                       "powerProduction": None,
                       "voltagePhase1": parent.PIN_O_LIVE_VOLTAGE_L1,
                       "voltagePhase2": parent.PIN_O_LIVE_VOLTAGE_L2,
                       "voltagePhase3": parent.PIN_O_LIVE_VOLTAGE_L3,
                       "currentL1": parent.PIN_O_LIVE_CURRENT_L1,
                       "currentL2": parent.PIN_O_LIVE_CURRENT_L2,
                       "currentL3": parent.PIN_O_LIVE_CURRENT_L3,
                       "accumulatedConsumption": parent.PIN_O_LIVE_ACCUMULATED_CONSUMPTION,
                       "accumulatedCost": parent.PIN_O_LIVE_ACCUMULATED_COST,
                       "lastMeterConsumption": parent.PIN_O_LIVE_METER_CONSUMPTION,
                       "lastMeterProduction": parent.PIN_O_LIVE_METER_FEEDIN
                       }
        self.ws = websocket.WebSocketApp(websocket_url, on_open=self.onconn, on_message=self.onmsg, on_close=self.onclose,
                                         on_error=self.onerror,
                                    header={'User-Agent': 'Gira HomeServer LBS Beta by S. Bunge '},
                                    subprotocols=["graphql-transport-ws"])

    def onconn(self, ws):
        """
        Register the websocket like a graphql-ws transport - including the auth.
        """
        ws.send('{"type":"connection_init","payload":{"token":"' + self.token + '"}}')
        self.help.log_debug("WS state", "sent auth")

    def onmsg(self, ws, msg):
        """
        After sending the auth we get an connection_ack back. Then we can ask for the data we want listen for.
        The data is send with a next type
        """
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
            for key in set(self.values.keys()) - {'power', 'powerProduction'}:  # Filter power values and calc later
                # Skip voltage and current information if not enabled
                self.help.set_output_sbc(self.values[key], livedata[key])

            # Calculate Power output (negative = feed-in)
            consumption = livedata['power']
            production = livedata['powerProduction']
            self.help.set_output_sbc(self.values['power'], consumption - production)

            self.last_data_recv_time = datetime.datetime.now()
            self.help.log_debug("WS state", "running: " + str(self.last_data_recv_time))
        elif tpe and tpe == "complete":
            # I guess complete is when the pulse went offline after successful transmission
            self.help.log_debug("WS state", "got complete - ending thread")
            self.stop()
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


class hourlyPriceInfo():

    def __init__(self, hour, price):
        self.hour = hour
        self.price = price

