from jsonclient import JsonClient


class HSL2Helper:

    def __init__(self, hs_module_context):
        self.lbs = hs_module_context
        self.DEBUG = None
        self.output_cache = {}

    def set_output_sbc(self, output_num, value):
        try:  # Catch this just if the queue gets full between check and write
            if self.output_cache.get(output_num) != value and self.lbs._can_set_output():
                self.lbs._set_output_value(output_num, value)
                self.output_cache[output_num] = value
        except Exception:
            self.log_err("exception while writing to output")

        return self  # for chaining

    def set_output(self, output_num, value):
        try:
            if self.lbs._can_set_output():
                self.lbs._set_output_value(output_num, value)
                self.output_cache[output_num] = value
        except Exception:
            self.log_err("exception while writing to output")

        return self  # for chaining

    def get_last_output_value(self, output_num):
        return self.output_cache[output_num]

    def create_debug(self):
        if not self.DEBUG:
            self.DEBUG = self.lbs.FRAMEWORK.create_debug_section()

    def log_debug(self, key, value):
        if bool(self.lbs._get_input_value(self.lbs.PIN_I_ENABLE_DEBUG)):
            self.create_debug()
            self.DEBUG.set_value(key, str(value))

    def log_msg(self, msg):
        if bool(self.lbs._get_input_value(self.lbs.PIN_I_ENABLE_DEBUG)):
            self.create_debug()
            self.DEBUG.add_message(msg)

    def log_err(self, msg):
        if bool(self.lbs._get_input_value(self.lbs.PIN_I_ENABLE_DEBUG)):
            self.create_debug()
            self.DEBUG.add_exception(msg)

    def new_json_client(self, endpoint, headers=None):
        json_client = JsonClient(endpoint, self, headers)
        return json_client
