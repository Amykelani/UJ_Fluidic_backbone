from Devices.stepperMotor import StepperMotor, LinearStepperMotor
from Devices.devices import Device, TempSensor, Heater, MagStirrer
from threading import Lock


class Module:
    """
    Class for representing generic modules. __init__ associates attached devices and creates instance attributes having
    those names.
    """
    def __init__(self, name, module_info, cmduino, manager):
        """
        :param name: String: the name of the module. E.g: "selectorvalve1", "syringepump2"
        :param manager: Manager object that is overseeing the robot functions
        :param module_info: dictionary containing device info for module and configuration info for module.
        :param cmduino: commanduino object that deals with low-level commands to Arduino.
        """
        # todo add method for adding modules after initialisation.
        assoc_devices = module_info["devices"]
        self.name = name
        self.steppers = []
        self.endstops = []
        self.he_sensors = []
        self.mag_stirrers = []
        self.heaters = []
        self.temp_sensors = []
        self.manager = manager
        self.lock = Lock()
        self.stop_lock = Lock()
        self.stop_cmd = False
        self.ready = True
        if module_info['mod_type'] != 'flask':
            for item in assoc_devices.keys():
                if 'stepper' in item:
                    # stepper dict: {..."stepper" : [ "cmd_stepper", "cmd_enabler"]...}
                    stepper = getattr(cmduino, assoc_devices[item]["name"])
                    enable_pin = getattr(cmduino, assoc_devices[item]["enable_pin"])
                    if module_info["mod_config"]["linear_stepper"]:
                        self.steppers.append(LinearStepperMotor(stepper, enable_pin, assoc_devices[item]["device_config"],
                                                                manager.serial_lock))
                    else:
                        self.steppers.append(StepperMotor(stepper, enable_pin, assoc_devices[item]["device_config"],
                                                          manager.serial_lock))
                elif 'endstop' in item:
                    endstop = getattr(cmduino, assoc_devices[item]["cmd_id"])
                    self.endstops.append(Device(endstop, manager.serial_lock))
                elif 'he_sens' in item:
                    he_sens = getattr(cmduino, assoc_devices[item]["cmd_id"])
                    self.he_sensors.append(Device(he_sens, manager.serial_lock))
                elif 'mag_stirrer' in item:
                    stirrer = getattr(cmduino, assoc_devices[item]['cmd_id'])
                    self.mag_stirrers.append(MagStirrer(stirrer, assoc_devices[item]["device_config"], manager.serial_lock))
                elif 'heater' in item:
                    heater = getattr(cmduino, assoc_devices[item]['cmd_id'])
                    self.heaters.append(Heater(heater, assoc_devices[item]["device_config"], manager.serial_lock))
                elif 'temp_sensor' in item:
                    temp_sensor = getattr(cmduino, assoc_devices[item]['cmd_id'])
                    self.temp_sensors.append(TempSensor(temp_sensor, assoc_devices[item]["device_config"], manager.serial_lock))

    def write_to_gui(self, message):
        command_dict = {'mod_type': 'gui', 'module_name': 'gui', 'command': 'write', 'message': message, 'parameters': {}}
        self.manager.q.put(command_dict)

    def stop(self):
        pass

    def resume(self, command_dict):
        return False


class FBFlask(Module):
    """
    Class to represent flasks in the fluidic backbone.
    """
    def __init__(self, name, module_info, cmd_mng, manager):
        super(FBFlask, self).__init__(name, module_info, cmd_mng, manager)
        self.type = "FSK"
        self.manager = manager
        module_config = module_info['mod_config']
        self.contents = module_config['Contents']
        self.contents_hist = []
        self.cur_vol = float(module_config['Current volume'])*1000
        self.max_volume = float(module_config['Maximum volume'])*1000

    def change_volume(self, vol):
        if self.check_volume(vol):
            self.cur_vol += vol
            if self.cur_vol == 0:
                self.contents = 'empty'
            return True
        return False

    def check_volume(self, vol):
        # if syringe aspirating (+vol), flask volume reduces. If syringe dispensing (-vol), flask volume increases.
        vol = -vol
        if vol < 0:
            if self.cur_vol + vol < 0:
                self.write_to_gui(f'Max volume of {self.name} would be exceeded')
                return False
        else:
            if self.cur_vol + vol > self.max_volume:
                self.write_to_gui(f'Insufficient {self.contents} in {self.name}')
                return False
        return True

    def change_contents(self, new_contents, vol):
        if self.change_volume(vol):
            self.contents_hist.append(self.contents)
            self.contents = new_contents