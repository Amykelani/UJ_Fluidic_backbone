import tkinter as tk
import os
import sys
import subprocess
import serial.tools.list_ports
import json
from PIL import ImageTk, Image
import cv2 as cv
import numpy as np
import networkx as nx

FIELD_NAMES = {"Maximum volume in ml": "max_volume",
               "Current volume in ml": "cur_volume",
               "Aluminium volume [m3]": "aluminium_volume",
               "Name": "name",
               "Fan speed RPM": "fan_speed",
               "Maximum samples": "max_samples",
               "Contents": "contents"
               }

UNITS = {"max_volume": "float",
         "cur_volume": "float",
         "fan_speed": "int",
         "max_samples": "int"}


def start_gui():
    root = tk.Tk()
    SetupGUI(root)
    root.mainloop()


def populate_ports():
    """
    Gets the serial ports available for connection
    :return: List of Arduinos available on the system
    """
    if sys.platform.startswith("win"):
        arduino_list = [port for port in serial.tools.list_ports.comports() if "arduino" in port.description.lower()]
    elif sys.platform.startswith("linux") or sys.platform.startswith("cygwin"):
        arduino_list = [port for port in serial.tools.list_ports.comports() if "acm" in port.description.lower()]
    else:
        raise EnvironmentError("Unsupported platform")

    return [name.name for name in arduino_list]


class CmdConfig:
    def __init__(self):
        self.ios = []
        self.devices = {}

    def load_existing(self, ios, devices):
        self.ios = ios
        self.devices = devices

    def as_dict(self):
        return {"ios": self.ios, "devices": self.devices}


class SetupGUI:
    def __init__(self, primary):
        # todo select connections from graph file
        # todo add means to change syringe start position
        self.script_dir = os.path.dirname(__file__)

        self.fonts = {"buttons": ("Calibri", 12), "labels": ("Calibri", 14), "default": ("Calibri", 16),
                      "heading": ("Calibri", 16), "text": ("Calibri", 14)}
        self.colours = {"accept-button": "#4de60b", "cancel-button": "#e6250b",
                        "heading": "#e65525", "other-button": "#45296e", "other-button-text": "#FFFFFF",
                        "form-bg": "#b5d5ff"}
        self.primary = primary
        self.primary.title("Fluidic backbone setup")
        self.primary.configure(background="#FFFFFF")
        self.key = ""
        self.id = ""
        self.rxn_name = ""
        self.frame = np.array([])
        self.roi = []

        self.setup_frame = tk.Frame(self.primary, bg=self.colours["form-bg"], borderwidth=5)
        self.utilities_frame = tk.Frame(self.primary, bg=self.colours["form-bg"], borderwidth=2)
        self.log_frame = tk.Frame(self.primary)
        self.log = tk.Text(self.log_frame, state="disable", width=80, height=16, wrap="none", borderwidth=5)

        self.setup_label = tk.Label(self.primary, text="Fluidic backbone setup:", font=self.fonts["heading"],
                                    fg=self.colours["heading"], bg="#FFFFFF",
                                    padx=2)
        self.utilities_label = tk.Label(self.primary, text="Utilities", font=self.fonts["heading"], padx=2,
                                        bg="#ffffff", fg=self.colours["heading"])

        self.log_frame.grid(row=4, column=2, padx=5, pady=10)
        self.log.grid(row=0, column=0)
        self.setup_label.grid(row=2, column=2)
        self.utilities_label.grid(row=2, column=10)
        self.setup_frame.grid(row=3, column=2)
        self.utilities_frame.grid(row=3, column=10)

        self.text_temp = ""
        self.int_temp = 0
        self.com_ports = []
        self.cmd_devices = CmdConfig()
        self.modules = {}
        self.graph = nx.MultiGraph()
        self.graph_tmp = nx.MultiGraph()
        self.node_config = None
        self.num_syringes = 0
        self.num_valves = 0
        self.conf_syr = 0
        self.conf_valves = 0
        self.conf_storage = 0
        self.num_he_sens = 0
        self.valves_buttons = {}
        self.config_cmd_flag = False
        self.config_cxn_flag = False
        self.es_options = {"X min": 3, "X max": 2, "Y min": 14, "Y max": 15, "Z min": 18, "Z max": 19}
        self.motor_configs = {"default": {"steps_per_rev": 3200, "enabled_acceleration": False, "speed": 1000,
                                          "max_speed": 10000, "acceleration": 1000},
                              "cmd_default": {"enabled_acceleration": False, "speed": 1000, "max_speed": 10000,
                                              "acceleration": 1000},
                              "valve": {"steps_per_rev": 3200, "enabled_acceleration": False, "speed": 1000,
                                        "max_speed": 4000, "acceleration": 1000}
                              }
        self.motor_options = {"X": {"stepperX": {"cmd_id": "STPX",
                                                 "device_config": {}}},
                              "Y": {"stepperY": {"cmd_id": "STPY",
                                                 "device_config": {}}},
                              "Z": {"stepperZ": {"cmd_id": "STPZ",
                                                 "device_config": {}}},
                              "E0": {"stepperE0": {"cmd_id": "STPE0",
                                                   "device_config": {}}},
                              "E1": {"stepperE1": {"cmd_id": "STPE1",
                                                   "device_config": {}}}}
        self.default_running_config = {
            "url": "http://127.0.0.1:5000/robots_api",
            "magnet_readings": {"valve1": {"1": 0, "3": 0, "5": 0, "7": 0, "9": 0}, "valve2": {"1": 0, "3": 0,
                                                                                               "5": 0, "7": 0, "9": 0},
                                "check_magnets": 0},
            "valve_backlash": {"valve1": {"check_backlash": 0, "backlash_steps": 0},
                               "valve2": {"check_backlash": 0, "backlash_steps": 0}},
            "valve_pos": {"valve1": None, "valve2": None}}
        self.used_motor_connectors = {}
        self.used_endstop_connectors = {}
        self.used_he_pins = []
        self.used_valves = []
        self.config_filenames = ["configs/cmd_config.json", "configs/module_connections.json",
                                 "configs/running_config.json"]

        image_dir = os.path.join(self.script_dir, "valve.png")
        self.valve_image = ImageTk.PhotoImage(Image.open(image_dir))

        self.simulation = False
        self.exit_flag = False
        steppers = [("stepperX", "STPX"), ("stepperY", "STPY"), ("stepperZ", "STPZ"),
                    ("stepperE0", "STPE0"), ("stepperE1", "STPE1")]
        for stepper in steppers:
            self.cmd_devices.devices[stepper[0]] = {"command_id": stepper[1],
                                                    "config": self.motor_configs["default"]}
        self.init_setup_panel()
        self.init_utilities_panel()

    def init_setup_panel(self):
        def display_ports(ports, refresh=False):
            if ports:
                i = 0
                label = tk.Label(com_frame, text="Available ports:", font=self.fonts["heading"],
                                 bg=self.colours["form-bg"], fg=self.colours["heading"])
                label.grid(row=2, columnspan=2)

                for name in ports:
                    c_port_button = tk.Button(com_frame, text="Arduino on " + name, font=button_font,
                                              bg=self.colours["other-button"],
                                              fg=self.colours["other-button-text"],
                                              command=lambda: add_com_port(name))
                    c_port_button.grid(row=3, column=i)
                    i += 1
            else:
                ports = populate_ports()
                if ports and refresh:
                    display_ports(ports)

        def add_com_port(port_name=""):
            port = ""
            if port_name == "":
                port = self.text_temp
                self.cmd_devices.ios.append({"port": port})
                self.write_message(f"Port {port} added")
                com_port_entry.delete(0, "end")
            else:
                if "tty" in port_name:
                    port_name = "/dev/" + port_name
                self.cmd_devices.ios.append({"port": port_name})
                self.write_message(f"Port {port_name} added")

        def add_key():
            self.key = self.text_temp
            robot_key_entry.delete(0, "end")
            self.write_message(f"Robot key added")

        def add_id():
            self.id = self.text_temp
            robot_id_entry.delete(0, "end")
            self.write_message(f"Robot ID added")

        def add_rxn_name():
            self.rxn_name = reaction_name_entry.get()
            reaction_name_entry.delete(0, "end")
            self.write_message(f"Reaction name {self.rxn_name} added")

        button_font = self.fonts["buttons"]
        com_frame = tk.Frame(self.setup_frame, bg=self.colours["form-bg"], pady=4)
        com_frame.grid(row=2)

        com_port_label = tk.Label(self.setup_frame, text="Choose an arduino to connect to, or write the name of the "
                                                         "com port:",
                                  font=self.fonts["labels"], fg=self.colours["heading"], bg=self.colours["form-bg"])
        com_port_label.grid(row=1, column=0)
        avail_ports = populate_ports()
        refresh_button = tk.Button(com_frame, text="Refresh", font=button_font, bg="LemonChiffon2",
                                   fg="black", command=lambda: display_ports(avail_ports, refresh=True))
        refresh_button.grid(row=4, column=2)
        display_ports(avail_ports)

        val_text = self.primary.register(self.validate_text)

        com_port_entry = tk.Entry(com_frame, validate="key", validatecommand=(val_text, "%P"),
                                  bg="#FFFFFF", fg="black", width=25)
        com_port_button = tk.Button(com_frame, text="Accept port", font=self.fonts["buttons"], bg="lawn green",
                                    fg="black", command=add_com_port)

        com_port_entry.grid(row=4, column=0, padx=4)
        com_port_button.grid(row=4, column=1, padx=4)

        robot_id_label = tk.Label(com_frame, text="Please enter the robot ID", bg=self.colours["form-bg"],
                                  font=self.fonts["labels"], fg=self.colours["heading"])
        robot_id_entry = tk.Entry(com_frame, validate="key", validatecommand=(val_text, "%P"), bg="#FFFFFF", fg="black",
                                  width=25)
        robot_id_button = tk.Button(com_frame, text="Accept ID", font=button_font, bg="lawn green", fg="black",
                                    command=add_id)

        robot_key_label = tk.Label(com_frame, text="Please enter the robot key", font=self.fonts["labels"],
                                   bg=self.colours["form-bg"], fg=self.colours["heading"])
        robot_key_entry = tk.Entry(com_frame, validate="key", validatecommand=(val_text, "%P"), bg="#FFFFFF",
                                   fg="black", width=25)
        robot_key_button = tk.Button(com_frame, text="Accept key", font=button_font, bg="lawn green", fg="black",
                                     command=add_key)

        robot_id_label.grid(row=5, column=0, padx=4)
        robot_id_entry.grid(row=5, column=1, padx=4)
        robot_id_button.grid(row=5, column=2, padx=4)
        robot_key_label.grid(row=6, column=0, padx=4)
        robot_key_entry.grid(row=6, column=1, padx=4)
        robot_key_button.grid(row=6, column=2, padx=4)

        mod_frame = tk.Frame(self.setup_frame, bg=self.colours["form-bg"])
        mod_label = tk.Label(mod_frame, text="Backbone modules and connections setup", font=self.fonts["labels"],
                             bg=self.colours["form-bg"], fg=self.colours["heading"])
        mod_button = tk.Button(mod_frame, text="Configure modules", font=button_font, bg=self.colours["other-button"],
                               fg=self.colours["other-button-text"], command=self.graph_setup)
        reaction_name_label = tk.Label(mod_frame, text="Please enter reaction name: ", font=self.fonts["labels"],
                                       bg=self.colours["form-bg"], fg=self.colours["heading"])
        reaction_name_entry = tk.Entry(mod_frame, width=20)
        reaction_name_butt = tk.Button(mod_frame, text="Accept name", font=self.fonts["buttons"],
                                       bg=self.colours["accept-button"], command=add_rxn_name)
        gen_button = tk.Button(mod_frame, text="Create config", font=button_font, bg="lawn green",
                               fg="black", command=self.generate_config)

        mod_frame.grid(row=3)
        mod_label.grid(row=1, column=0, columnspan=3)
        mod_button.grid(row=2, column=0, columnspan=3, pady=4)
        reaction_name_label.grid(row=3, column=0)
        reaction_name_entry.grid(row=3, column=1)
        reaction_name_butt.grid(row=3, column=2, padx=5)
        gen_button.grid(row=4, column=0, columnspan=3)

    def init_utilities_panel(self):
        def clear_configs():
            self.graph = nx.MultiGraph()
            self.graph_tmp = nx.MultiGraph()
            self.cmd_devices = CmdConfig()
            self.num_valves = 0
            self.num_syringes = 0
            self.config_cmd_flag = False
            self.config_cxn_flag = False

        button_font = self.fonts["buttons"]
        run_fb_button = tk.Button(self.utilities_frame, text="Run Fluidic Backbone", font=self.fonts["buttons"],
                                  bg="DeepSkyBlue", fg="black", command=self.run_fb_menu)
        lc_butt = tk.Button(self.utilities_frame, text="Load existing configuration", font=button_font,
                            bg=self.colours["other-button"], fg=self.colours["other-button-text"],
                            command=lambda: self.load_configs())
        cc_butt = tk.Button(self.utilities_frame, text="Clear configuration", font=self.fonts["buttons"],
                            bg="Tomato2", fg="black", command=clear_configs)

        lc_butt.grid(row=1, column=0, padx=4, pady=4)
        cc_butt.grid(row=2, column=0, padx=4, pady=4)
        run_fb_button.grid(row=4, column=0, padx=4, pady=10)

    def graph_setup(self):
        def accept():
            if self.conf_valves > 0 and self.conf_syr > 0:
                self.config_cxn_flags = True
                self.config_cmd_flag = True
                self.graph = self.graph_tmp
                graph_setup.destroy()
            else:
                self.write_message("Required to configure at least one valve and syringe")

        def reset_graph_setup():
            self.modules = {}
            graph_setup.destroy()

        def populate_menus(frame, valve_no, row_count, port, col, pad=2, span=False):
            new_frame = tk.Frame(frame)
            col_span = 1
            if span:
                col_span = 2
            row = row_count * 2
            new_frame.grid(row=row, column=col, columnspan=col_span, pady=pad)
            module_type = tk.StringVar(new_frame)
            module_type.set("")
            port_button = tk.Button(new_frame, text=f"Configure port {port}", bg="LightBlue3", fg="black")
            port_button.grid(row=1, column=1)
            port_om = tk.OptionMenu(new_frame, module_type, *module_options)
            port_om.grid(row=2, column=1)
            port_button.configure(command=lambda v=valve_no,
                                  mt=module_type, p=port, pb=port_button: port_menu_start(v, mt, p, pb))
            self.valves_buttons[valve_name][port] = port_button
            node = self.get_node(valve_name, port)
            if node:
                port_button.configure(bg="lawn green")
                module_type.set(self.graph_tmp.nodes[node]["mod_type"])

        def port_menu_start(valve_no, module_type, port_no, button):
            variable = module_type.get()
            if variable != "":
                port_options_window = tk.Toplevel(self.primary)
                this_valve_name = f"valve{valve_no + 1}"
                valve_info = {"valve_name": this_valve_name, "valve_id": valve_no, "port_no": port_no}
                node_info = {"entries": []}
                title = tk.Label(port_options_window, text=f"Configure port {port_no} on {this_valve_name}",
                                 font=self.fonts["heading"], fg=self.colours["heading"])
                title.grid(row=0, column=0, columnspan=2)
                type_label = tk.Label(port_options_window, text=variable.capitalize(), font=self.fonts["heading"],
                                      fg=self.colours["heading"])
                type_label.grid(row=1, column=0, columnspan=2)
                found_node = self.get_node(this_valve_name, port_no)
                if variable == "flask":
                    node_info["mod_type"] = "flask"
                    node_info["class_type"] = "FBFlask"
                    fields = ["Name", "Current volume in ml", "Maximum volume in ml", "Contents",
                              "Tubing length in mm"]
                    self.flask_setup(node_info, valve_info, fields, port_options_window, button, found_node)
                elif variable == "reactor":
                    node_info["mod_type"] = "reactor"
                    node_info["class_type"] = "Reactor"
                    fields = ["Name", "Current volume in ml", "Maximum volume in ml",
                              "Contents", "Fan speed RPM", "Aluminium volume [m3] (eg. 1e-6)", "Tubing length in mm"]
                    self.reactor_setup(node_info, valve_info, fields, port_options_window, button, found_node)
                elif variable == "syringe":
                    node_info["mod_type"] = "syringe_pump"
                    node_info["class_type"] = "SyringePump"
                    fields = ["Current volume in ml", "Maximum volume in ml", "Contents"]
                    fields.pop(0)
                    self.syringe_setup(node_info, valve_info, fields, port_options_window, button, found_node)
                elif variable == "valve":
                    fields = ["Tubing length in mm"]
                    self.valve_link(node_info, valve_info, fields, port_options_window, button, found_node)
                elif variable == "waste":
                    node_info["mod_type"] = "waste"
                    node_info["class_type"] = "FBFlask"
                    node_info["Contents"] = "Waste"
                    fields = ["Name", "Current volume in ml", "Maximum volume in ml", "Tubing length in mm"]
                    self.flask_setup(node_info, valve_info, fields, port_options_window, button, found_node)
                elif variable == "filter":
                    node_info["mod_type"] = "filter"
                    node_info["class_type"] = "FBFlask"
                    fields = ["Name", "Current volume in ml", "Maximum volume in ml", "Dead volume in ml"]
                    self.flask_setup(node_info, valve_info, fields, port_options_window, button, found_node)
                elif variable == "storage":
                    node_info["mod_type"] = "storage"
                    node_info["class_type"] = "FluidStorage"
                    fields = ["Maximum volume in ml",
                              "Tubing length in mm", "Maximum samples"]
                    self.storage_setup(node_info, valve_info, fields, port_options_window, button, found_node)

        if self.num_valves == 0 or self.num_syringes == 0:
            if self.num_valves == 0:
                valves_query = tk.Toplevel(self.primary)
                valves_query.attributes("-topmost", "true")
                q_label = tk.Label(valves_query, text="How many valves are attached to the backbone?",
                                   font=self.fonts["heading"], fg=self.colours["heading"])
                validate_valves = valves_query.register(self.validate_int)
                q_entry = tk.Entry(valves_query, validate="key", validatecommand=(validate_valves, "%P"))
                ok_button = tk.Button(valves_query, text="Accept", bg="lawn green",
                                      command=lambda: self.add_mod("selector_valve", valves_query))
                cancel_button = tk.Button(valves_query, text="Cancel", bg="tomato2", command=valves_query.destroy)

                q_label.grid(row=0, column=1)
                q_entry.grid(row=1, column=1)
                ok_button.grid(row=2, column=0)
                cancel_button.grid(row=2, column=2)

            if self.num_syringes == 0:
                syringe_query = tk.Toplevel(self.primary)
                syringe_query.attributes("-topmost", "true")
                q_label = tk.Label(syringe_query, text="How many syringes are attached to the backbone?",
                                   font=self.fonts["heading"], fg=self.colours["heading"])
                validate_syr = syringe_query.register(self.validate_int)
                q_entry = tk.Entry(syringe_query, validate="key", validatecommand=(validate_syr, "%P"))
                ok_button = tk.Button(syringe_query, text="Accept", bg="lawn green",
                                      command=lambda: self.add_mod("syringe_pump", syringe_query))
                cancel_button = tk.Button(syringe_query, text="Cancel", bg="tomato2", command=syringe_query.destroy)

                q_label.grid(row=0, column=1)
                q_entry.grid(row=1, column=1)
                ok_button.grid(row=2, column=0)
                cancel_button.grid(row=2, column=2)
        else:
            graph_setup = tk.Toplevel(self.primary)
            graph_setup.title("Backbone connections setup")
            graph_setup.configure(bg="#ffffff")
            module_options = ["filter", "flask", "reactor", "storage", "syringe", "valve", "waste", ]
            for i in range(0, self.num_valves):
                valve_frame = tk.Frame(graph_setup)
                left_ports = tk.Frame(valve_frame)
                img_frame = tk.Frame(valve_frame)
                right_ports = tk.Frame(valve_frame)
                valve_name = f"valve{i + 1}"
                self.valves_buttons[valve_name] = {-1: None, 1: None, 2: None, 3: None, 4: None, 5: None, 6: None,
                                                   7: None, 8: None, 9: None, 10: None, "cfg": None}
                if not self.config_cxn_flag:
                    self.graph_tmp.add_node(valve_name)
                    self.graph_tmp.nodes[valve_name]["name"] = valve_name
                    self.graph_tmp.nodes[valve_name]["mod_type"] = "selector_valve"
                    self.graph_tmp.nodes[valve_name]["class_type"] = "SelectorValve"
                top_label = tk.Label(valve_frame, text=f"Valve {i + 1}", font=self.fonts["heading"],
                                     fg=self.colours["heading"])

                top_label.grid(row=0, column=1)
                valve_frame.grid(row=1, column=i, padx=10)
                img_frame.grid(row=1, column=1)
                left_ports.grid(row=1, column=0)
                right_ports.grid(row=1, column=2)

                for j, k in enumerate(range(2, 6)):
                    populate_menus(left_ports, valve_no=i, row_count=j, port=k, pad=5, col=0)

                image = tk.Label(img_frame, image=self.valve_image)
                image.grid(row=3, column=0, columnspan=2)
                populate_menus(img_frame, valve_no=i, row_count=0, port=1, col=0)
                populate_menus(img_frame, valve_no=i, row_count=0, port=-1, col=1)
                populate_menus(img_frame, valve_no=i, row_count=3, port=6, col=0, span=True)

                for j, k in enumerate(range(10, 6, -1)):
                    populate_menus(right_ports, valve_no=i, row_count=j, port=k, pad=5, col=2)

                self.valves_buttons[valve_name]["cfg"] = tk.Button(img_frame, text=f"Valve {i + 1} setup",
                                                                   font=self.fonts["buttons"], bg="LightBlue3",
                                                                   fg="black")
                self.valves_buttons[valve_name]["cfg"].grid(row=9, column=0, columnspan=2)
                self.valves_buttons[valve_name]["cfg"].configure(
                    command=lambda vn=valve_name, valve_butt=self.valves_buttons[valve_name]["cfg"]:
                    self.valve_setup({"valve_name": vn}, valve_butt))
                if self.graph_tmp.nodes[valve_name].get("mod_config"):
                    self.valves_buttons[valve_name]["cfg"].configure(bg="lawn green")
            camera_butt = tk.Button(graph_setup, text="Set up camera", bg=self.colours["other-button"], fg="white")
            camera_butt.configure(command=lambda: self.camera_setup(camera_butt))
            accept_butt = tk.Button(graph_setup, text="Accept", bg="lawn green", command=accept)
            cancel_butt = tk.Button(graph_setup, text="Cancel", bg="tomato2", command=reset_graph_setup)
            camera_butt.grid(row=2, column=0)
            accept_butt.grid(row=3, column=1)
            cancel_butt.grid(row=3, column=2)

    def add_mod(self, mod_type, popup):
        if mod_type == "syringe_pump":
            self.num_syringes = self.int_temp
        elif mod_type == "selector_valve":
            self.num_valves = self.int_temp
        popup.destroy()
        if self.num_syringes > 0 and self.num_valves > 0:
            self.graph_setup()

    def syringe_setup(self, node_info, valve_info, fields, window, button, found_node):
        def accept():
            motor_cxn = motor_connector.get()
            endstop = endstop_connector.get()
            select_new = False
            if motor_cxn and endstop:
                if motor_cxn in self.used_motor_connectors.keys() and not found_node:
                    select_new = True
                    self.write_message(
                        f"That motor connector is already used by {self.used_motor_connectors[motor_cxn]}")
                if endstop in self.used_endstop_connectors.keys() and not found_node:
                    select_new = True
                    self.write_message(
                        f"That endstop connector is already used by {self.used_endstop_connectors[endstop]}")
                if not select_new:
                    if not found_node:
                        self.conf_syr += 1
                        syringe_name = f"syringe{self.conf_syr}"
                        self.graph_tmp.add_node(syringe_name)
                    else:
                        syringe_name = self.graph_tmp.nodes[found_node]["name"]
                    node = self.graph_tmp.nodes[syringe_name]
                    node["name"] = syringe_name
                    stepper_name = f"stepper{motor_cxn}"
                    self.used_motor_connectors[motor_cxn] = syringe_name
                    self.used_endstop_connectors[endstop] = syringe_name
                    node["mod_type"] = "syringe_pump"
                    node["class_type"] = "SyringePump"
                    node["mod_config"] = {"screw_lead": 8, "linear_stepper": True, "backlash": 780}
                    node["devices"] = self.motor_setup(stepper_name, motor_cxn, config_type="default")
                    node["endstop"] = self.es_options[endstop]
                    self.read_fields(node_info, node)
                    self.add_edge(True, node["name"], valve_info["valve_name"], False,
                                  port=[valve_info["valve_id"], valve_info["port_no"]],
                                  tubing_length=0)
                    button.configure(bg="lawn green")
                    window.destroy()
                    self.config_cxn_flag = True
            else:
                if not motor_cxn:
                    self.write_message("Please select a motor connector")
                if not endstop:
                    self.write_message("Please select an endstop connector")

        label = tk.Label(window, text=f"syringe{self.conf_syr + 1}", font=self.fonts["heading"],
                         fg=self.colours["heading"])
        label.grid(row=2, column=0, columnspan=2)
        motor_connector = tk.StringVar(window)
        endstop_connector = tk.StringVar(window)

        motor_connection_label = tk.Label(window, text="Which motor connector is used for this syringe",
                                          font=self.fonts["heading"], fg=self.colours["heading"])
        motor_connection_label.grid(row=3, column=0)
        i = 4
        options = self.motor_options.keys()
        selected = self.used_motor_connectors.keys()
        for motor in options:
            tk.Radiobutton(window, text=motor, variable=motor_connector, value=motor).grid(row=i, column=0)
            i += 1
        motor_connector.set(self.find_unselected(options, selected))

        endstop_label = tk.Label(window, text="Which endstop connection is used for this syringe?",
                                 font=self.fonts["heading"], fg=self.colours["heading"])
        endstop_label.grid(row=9, column=0)
        i = 10
        options = self.es_options.keys()
        selected = self.used_endstop_connectors.keys()
        for option in options:
            tk.Radiobutton(window, text=option, variable=endstop_connector, value=option).grid(row=i, column=0)
            i += 1
        endstop_connector.set(self.find_unselected(options, selected))

        offset = i
        offset = self.generate_fields(node_info, window, fields, offset) + 1

        accept_button = tk.Button(window, text="Accept", fg="black", bg="lawn green", command=accept)
        cancel_button = tk.Button(window, text="Cancel", fg="black", bg="tomato2",
                                  command=window.destroy)
        accept_button.grid(row=offset, column=0)
        cancel_button.grid(row=offset, column=1)
        if found_node:
            this_node = self.graph_tmp.nodes[found_node]
            endstop_connector.set(self.get_key(this_node["endstop"], self.es_options))
            self.update_node_entries(node_info, valve_info, this_node)
            motor_connector.set(this_node["devices"]["stepper"]["name"][-1])

    def valve_setup(self, valve_info, valve_button):
        def accept(button):
            motor_cxn = motor_connector.get()
            try:
                pin = hall_connector.get()
                gear = geared_motor.get()
                hall_sensor = pins[pin]
            except KeyError:
                self.write_message("Please select a pin for the hall-effect sensor")
            else:
                if motor_cxn:
                    if motor_cxn in self.used_motor_connectors.keys() and not self.config_cxn_flag:
                        self.write_message(
                            f"That motor connector is already used by {self.used_motor_connectors[motor_cxn]}")
                    else:
                        if not self.config_cxn_flag or not devices:
                            self.num_he_sens += 1
                        valve_name = valve_info["valve_name"]
                        node = self.graph_tmp.nodes[valve_name]
                        stepper_name = f"stepper{motor_cxn}"
                        he_sens_name = f"he_sens{self.num_he_sens}"
                        self.used_motor_connectors[motor_cxn] = valve_name
                        self.used_he_pins.append(pin)
                        if gear == "":
                            gear = "Direct drive"
                        node["mod_config"] = {"ports": 10, "linear_stepper": False, "gear": gear}
                        node["devices"] = {}
                        node["devices"].update(
                            self.motor_setup(stepper_name, motor_cxn, config_type="valve"))
                        node["devices"]["he_sens"] = {"name": he_sens_name, "cmd_id": hall_sensor, "device_config": {}}
                        self.cmd_devices.devices[hall_sensor] = {"command_id": hall_sensor}
                        button.configure(bg="lawn green")
                        window.destroy()
                        self.config_cxn_flag = True
                        self.conf_valves += 1

        pins = {"Analog Read 1 (A3)": "AR1", "Analog Read 2 (A4)": "AR2"}
        window = tk.Toplevel(self.primary)
        label = tk.Label(window, text=f"Valve {self.conf_valves + 1}")
        label.grid(row=2, column=0, columnspan=2)
        motor_connector = tk.StringVar(window)
        hall_connector = tk.StringVar(window)
        geared_motor = tk.StringVar(window)

        motor_connection_label = tk.Label(window, text="Which motor connector is used for this valve?",
                                          font=self.fonts["heading"])
        motor_connection_label.grid(row=3, column=0)
        i = 4
        options = self.motor_options.keys()
        selected = self.used_motor_connectors.keys()
        for motor_cn in options:
            tk.Radiobutton(window, text=motor_cn, variable=motor_connector, value=motor_cn).grid(row=i, column=0)
            i += 1
        motor_connector.set(self.find_unselected(options, selected))

        hall_sensor_label = tk.Label(window, text="Which pin is the hall sensor plugged into?",
                                     font=self.fonts["heading"])
        hall_sensor_label.grid(row=9, column=0)
        hall_options = list(pins.keys())
        hall_sensor_selector = tk.OptionMenu(window, hall_connector, *hall_options)
        hall_sensor_selector.grid(row=10, column=0)

        gear_options = ["Direct drive", "1.5:1", "2:1", "3:1"]
        geared_motor.set("")
        gear_label = tk.Label(window, text="Gear options:", font=self.fonts["heading"])
        gear_label.grid(row=12)
        gear_selector = tk.OptionMenu(window, geared_motor, *gear_options)
        gear_selector.grid(row=13)

        offset = 14
        accept_button = tk.Button(window, text="Accept", fg="black", bg="lawn green",
                                  command=lambda: accept(valve_button))
        cancel_button = tk.Button(window, text="Cancel", fg="black", bg="tomato2",
                                  command=window.destroy)
        accept_button.grid(row=offset + 1, column=0)
        cancel_button.grid(row=offset + 1, column=1)
        config_valve = self.graph_tmp.nodes[valve_info["valve_name"]]
        devices = config_valve.get("devices")
        if self.config_cxn_flag and devices is not None:
            # set the hall pin
            found_node = self.graph_tmp.nodes[valve_info["valve_name"]]
            hall_connector.set(self.get_key(found_node["devices"]["he_sens"]["cmd_id"], pins))
            # set the motor using the stepper letter (X, Y, Z...)
            motor_connector.set(found_node["devices"]["stepper"]["name"][-1])
            # set the gear
            geared_motor.set(found_node["mod_config"]["gear"])

    def storage_setup(self, node_info, valve_info, fields, window, button, found_node):
        def accept():
            motor_cxn = motor_connector.get()
            select_new = False
            if motor_cxn in self.used_motor_connectors.keys() and not found_node:
                select_new = True
                self.write_message(f"That motor connector is already in use by {self.used_motor_connectors[motor_cxn]}")
            if not select_new:
                self.conf_storage += 1
                storage_name = f"storage{self.conf_storage}"
                if not self.graph_tmp.nodes.get(storage_name):
                    self.graph_tmp.add_node(storage_name)
                node = self.graph_tmp.nodes[storage_name]
                stepper_name = f"stepper{motor_cxn}"
                self.used_motor_connectors[motor_cxn] = storage_name
                node["name"] = storage_name
                node["mod_type"] = "storage"
                node["class_type"] = "FluidStorage"
                node["devices"] = self.motor_setup(stepper_name, motor_cxn, config_type="default")
                node["mod_config"] = {"linear_stepper": False}
                tubing_length = self.read_fields(node_info, node)
                self.add_edge(True, node["name"], valve_info["valve_name"], found_node,
                              port=[valve_info["valve_id"], valve_info["port_no"]],
                              tubing_length=tubing_length)
                button.configure(bg="lawn green")
                window.destroy()
                self.config_cxn_flag = True

        label = tk.Label(window, text="Storage setup", font=self.fonts["heading"], fg=self.colours["heading"])
        label.grid(row=2, column=0, columnspan=2)
        motor_connector = tk.StringVar(window)
        motor_connector_label = tk.Label(window, text="Which motor connector is used for the storage?",
                                         font=self.fonts["heading"], fg=self.colours["heading"])
        motor_connector_label.grid(row=3, column=0)
        options = self.motor_options.keys()
        selected = self.used_motor_connectors.keys()
        i = 4
        for motor in options:
            tk.Radiobutton(window, text=motor, variable=motor_connector, value=motor).grid(row=i, column=0)
            i += 1
        motor_connector.set(self.find_unselected(options, selected))
        offset = i
        offset = self.generate_fields(node_info, window, fields, offset) + 1
        accept_button = tk.Button(window, text="Accept", fg="black", bg="lawn green", command=accept)
        cancel_button = tk.Button(window, text="Cancel", fg="black", bg="tomato2", command=window.destroy)
        accept_button.grid(row=offset, column=0)
        cancel_button.grid(row=offset, column=1)
        if found_node:
            this_node = self.graph_tmp.nodes[found_node]
            # get the stepper letter (X, Y, Z...)
            motor_connector.set(self.graph_tmp.nodes[found_node]["devices"]["stepper"]["name"][-2:])
            self.update_node_entries(node_info, valve_info, this_node)

    def camera_setup(self, camera_button):
        def accept():
            self.graph_tmp.add_node("camera1")
            node = self.graph_tmp.nodes["camera1"]
            node["name"] = "camera1"
            node["mod_type"] = "camera"
            node["class_type"] = "Camera"
            node["mod_config"] = {"ROI": self.roi}
            camera_button.configure(bg="lawn green")
            cap.release()
            cv.destroyAllWindows()
            window.destroy()

        def cancel():
            cap.release()
            cv.destroyAllWindows()
            window.destroy()

        def video_stream():
            _, self.frame = cap.read()
            img = cv.cvtColor(self.frame, cv.COLOR_BGR2RGBA)
            tkimg = Image.fromarray(img)
            imgtk = ImageTk.PhotoImage(image=tkimg)
            img_label.imgtk = imgtk
            img_label.configure(image=imgtk)
            img_label.after(1, video_stream)

        def setup_roi():
            warning2 = tk.Toplevel(window)
            warn_label2 = tk.Label(warning2, text="Press space or enter when done. Press c to cancel")
            warn_label2.grid()
            self.roi = cv.selectROI("Select ROI", self.frame)
            warning2.destroy()
            cv.destroyAllWindows()

        window = tk.Toplevel(self.primary)
        cap = cv.VideoCapture(0)
        label = tk.Label(window, text="Camera", font=self.fonts["heading"], fg=self.colours["heading"])
        label.grid(row=1, column=0, columnspan=2)
        label = tk.Label(window, text="Please place the camera, then use the button to set the region of interest.",
                         font=self.fonts["labels"])
        img_label = tk.Label(window)
        label.grid(row=2, column=0, columnspan=2)
        img_label.grid(row=3, column=0, columnspan=2)
        roi_butt = tk.Button(window, text="Configure ROI", font=self.fonts["buttons"], bg=self.colours["other-button"],
                             command=setup_roi)
        roi_butt.grid(row=4, column=0, columnspan=2)
        accept_butt = tk.Button(window, text="Accept", font=self.fonts["buttons"], bg=self.colours["accept-button"],
                                command=accept)
        cancel_butt = tk.Button(window, text="Cancel", font=self.fonts["buttons"], bg=self.colours["cancel-button"],
                                command=cancel)
        accept_butt.grid(row=5, column=1)
        cancel_butt.grid(row=5, column=3)
        video_stream()

    def valve_link(self, node_info, valve_info, fields, window, button, found_node):
        """Set up a link between two valves

        Args:
            node_config (NodeConfig Object): Object that describes the graph node
            window (tkinter Window Object): Parent window of this menu
            button (Tkinter Button): The button to colour once this method is run
        """

        def accept_valve_link(sel_valve, tube_length, valve_button):
            valve_name = sel_valve.get()
            if valve_name != "":
                valve = self.graph_tmp.nodes[valve_name]
                self.used_valves.append(valve_name)
                node = {"mod_config": {}}
                if tube_length == 0:
                    tube_length = self.read_fields(node_info, node)
                self.add_edge(True, valve["name"], valve_info["valve_name"], found_node,
                              port=[valve_info["valve_id"], valve_info["port_no"]],
                              tubing_length=tube_length)
                valve_button.configure(bg="lawn green")
                window.destroy()
                self.config_cxn_flag = True
            else:
                self.write_message("Please select a valve")

        tubing_length = 0
        possible_valves = [m for m in self.graph_tmp.nodes.keys() if "valve" in m]
        selected_valve = tk.StringVar(window)
        selector_label = tk.Label(window, text="Select a valve:")
        valve_selector = tk.OptionMenu(window, selected_valve,
                                       *possible_valves)
        selected_valve.set(self.find_unselected(possible_valves, self.used_valves))
        selector_label.grid()
        offset = self.generate_fields(node_info, window, fields, 1)
        valve_selector.grid(row=offset + 1, column=1)
        if found_node:
            selected_valve.set(found_node)
            tubing_length = self.graph_tmp.adj[valve_info["valve_name"]][found_node][0]["tubing_length"]
            self.update_node_entries(node_info, valve_info, self.graph_tmp.nodes[found_node])
        valve_ok = tk.Button(window, text="Accept", fg="black", bg="lawn green",
                             command=lambda sel_valve=selected_valve, tube_len=tubing_length: accept_valve_link(
                                 sel_valve, tube_len, button))
        cancel_butt = tk.Button(window, text="Cancel", fg="black",
                                bg="tomato2", command=window.destroy)
        valve_ok.grid(row=offset + 2, column=1)
        cancel_butt.grid(row=offset + 2, column=2)

    def motor_setup(self, stepper_name, motor_cn, config_type):
        this_motor_config = {"name": stepper_name}
        motor_options = self.motor_options[motor_cn][stepper_name]
        motor_options["device_config"].update(self.motor_configs[config_type])
        this_motor_config.update(motor_options)
        return {"stepper": this_motor_config}

    def flask_setup(self, node_info, valve_info, fields, window, button, found_node):
        def accept_flask(flask_button):
            flask_name = node_info["entries"][0][1].get()
            self.graph_tmp.add_node(flask_name)
            node = self.graph_tmp.nodes[flask_name]
            node["name"] = flask_name
            node["mod_config"] = {}
            node["mod_type"] = "flask"
            tubing_length = self.read_fields(node_info, node)
            self.add_edge(True, node["name"], valve_info["valve_name"], found_node,
                          port=[valve_info["valve_id"], valve_info["port_no"]],
                          tubing_length=tubing_length)
            flask_button.configure(bg="lawn green")
            window.destroy()
            self.config_cxn_flag = True

        offset = self.generate_fields(node_info, window, fields, 2) + 1
        flask_ok = tk.Button(window, text="Accept", fg="black", bg="lawn green", command=lambda: accept_flask(button))
        flask_cancel = tk.Button(window, text="Cancel", fg="black", bg="tomato2",
                                 command=window.destroy)
        flask_ok.grid(row=offset, column=1)
        flask_cancel.grid(row=offset, column=2)
        if found_node:
            this_node = self.graph_tmp.nodes[found_node]
            self.update_node_entries(node_info, valve_info, this_node)

    def reactor_setup(self, node_info, valve_info, fields, window, button, found_node):
        def accept_reactor(reactor_button):
            try:
                stirrer = stir_pin.get()
                heater = heat_pin.get()
                thermistor = temp_pin.get()
                stirrer = pins[stirrer]
                heater = pins[heater]
            except KeyError:
                self.write_message("Please select pins for the reactor devices")
            else:
                reactor_name = node_info["entries"][0][1].get()
                self.graph_tmp.add_node(reactor_name)
                node = self.graph_tmp.nodes[reactor_name]
                node["name"] = reactor_name
                node["mod_config"] = {}
                node["mod_type"] = "reactor"
                tubing_length = self.read_fields(node_info, node)
                node["devices"] = {"heater": {"name": "heater1", "cmd_id": heater, "device_config": {}},
                                   "mag_stirrer": {"name": "stirrer1", "cmd_id": stirrer,
                                                   "device_config": {"fan_speed": node["mod_config"]["fan_speed"]}},
                                   "temp_sensor": {"name": "temp_sensor1", "cmd_id": thermistor,
                                                   "device_config": {"SH_C": [0.0008271125019925238,
                                                                              0.0002088017729221142,
                                                                              8.059262669466295e-08]}}}
                self.add_edge(True, node["name"], valve_info["valve_name"], found_node,
                              port=[valve_info["valve_id"], valve_info["port_no"]],
                              tubing_length=tubing_length)
                self.cmd_devices.devices[thermistor] = {"command_id": thermistor}
                self.cmd_devices.devices[stirrer] = {"command_id": stirrer}
                self.cmd_devices.devices[heater] = {"command_id": heater}
                reactor_button.configure(bg="lawn green")
                window.destroy()
                self.config_cxn_flag = True

        pins = {"D8": "AW1", "D9": "AW2", "D10": "AW3"}
        temp_pins = ["T1", "T2"]
        heat_pin = tk.StringVar()
        stir_pin = tk.StringVar()
        temp_pin = tk.StringVar()

        offset = self.generate_fields(node_info, window, fields, 2) + 1
        pin_heat_label = tk.Label(window, text="Which pin is the heater connected to?")
        pin_heat_selector = tk.OptionMenu(window, heat_pin, *list(pins.keys()))
        pin_heat_label.grid(row=offset)
        pin_heat_selector.grid(row=offset, column=1)

        pin_stir_label = tk.Label(window, text="Which pin is the stirrer connected to?")
        pin_stir_label.grid(row=offset + 1)
        pin_stir_selector = tk.OptionMenu(window, stir_pin, *list(pins.keys()))
        pin_stir_selector.grid(row=offset + 1, column=1)

        tpin_label = tk.Label(window, text="Which pin is the thermistor attached to?")
        tpin_label.grid(row=offset + 2)
        tpin_selector = tk.OptionMenu(window, temp_pin, *temp_pins)
        tpin_selector.grid(row=offset + 2, column=1)

        reactor_ok = tk.Button(window, text="Accept", fg="black", bg="lawn green",
                               command=lambda: accept_reactor(button))
        reactor_ok.grid(row=offset + 3)
        reactor_cancel = tk.Button(window, text="Cancel", fg="black",
                                   bg="tomato2", command=window.destroy)
        reactor_cancel.grid(row=offset + 3, column=2)
        if found_node:
            this_node = self.graph_tmp.nodes[found_node]
            heat_pin.set(self.get_key(this_node["devices"]["heater"]["cmd_id"], pins))
            temp_pin.set(this_node["devices"]["temp_sensor"]["cmd_id"])
            stir_pin.set(self.get_key(this_node["devices"]["mag_stirrer"]["cmd_id"], pins))
            self.update_node_entries(node_info, valve_info, this_node)

    def validate_text(self, new_text):
        if not new_text:
            self.text_temp = ""
            return True
        try:
            self.text_temp = str(new_text)
            return True
        except ValueError:
            return False

    def validate_int(self, new_int):
        if not new_int:
            self.int_temp = 0
            return True
        try:
            self.int_temp = int(new_int)
            return True
        except ValueError:
            return False

    @staticmethod
    def get_key(value, search_dict):
        for k, v in search_dict.items():
            if v == value:
                return k

    def update_node_entries(self, node_info, valve_info, node):
        for f in node_info["entries"]:
            if f[0] == "Tubing length in mm":
                edges = self.graph_tmp.adj[node["name"]][valve_info["valve_name"]]
                tubing_length = edges[0]["tubing_length"]
                f[1].insert(0, tubing_length)
            else:
                text = node["mod_config"].get(FIELD_NAMES.get(f[0], f[0]))
                f[1].insert(0, text)

    @staticmethod
    def find_unselected(possible_options, selected_options):
        options = list(possible_options)
        selected = list(selected_options)
        for option in options:
            if option not in selected:
                return option

    @staticmethod
    def generate_fields(node_info, frame, field_list, offset):
        # todo add validation to volume entries
        index = 0
        for index, field in enumerate(field_list):
            label = tk.Label(frame, text=field)
            label.grid(row=index + offset, column=0)
            entry = tk.Entry(frame)
            entry.grid(row=index + offset, column=1)
            node_info["entries"].append((field, entry))
        return index + offset

    @staticmethod
    def read_fields(node_info, node, start_field=0):
        entries = node_info["entries"]
        tubing_length = 0
        for i in range(start_field, len(entries)):
            field = entries[i][0]
            if field == "Tubing length in mm":
                try:
                    tubing_length = float(entries[i][1].get())
                except ValueError:
                    tubing_length = 0
            else:
                config = entries[i][1].get()
                field = FIELD_NAMES.get(field, field)
                units = UNITS.get(field)
                if units is None:
                    config = str(config)
                elif units == "float":
                    config = float(config)
                elif units == "int":
                    config = int(config)
                node["mod_config"].update([(field, config)])
        return tubing_length

    def get_node(self, valve_name, port):
        adj_nodes = self.graph_tmp.adj[valve_name]
        for node in adj_nodes:
            for edge in adj_nodes[node]:
                if adj_nodes[node][edge]["port"][1] == port:
                    return node
        return ""

    @staticmethod
    def delete_fields(o_frame):
        for widget in o_frame.winfo_children():
            widget.destroy()

    def add_edge(self, dual, *args, **kwargs):
        if args[2]:
            self.graph_tmp.adj[args[0]][args[1]][0]["tubing_length"] = kwargs["tubing_length"]
        else:
            self.graph_tmp.add_edge(args[0], args[1], **kwargs)
            if dual:
                self.graph_tmp.add_edge(args[1], args[0], **kwargs)

    def run_fb_menu(self):
        run_popup = tk.Toplevel(self.primary)
        run_popup.title("Run Fluidic Backbone")
        warning_label = tk.Label(run_popup,
                                 text="Have you finished configuring the system? Selecting yes will use configuration "
                                      "stored in configs folder.",
                                 font=self.fonts["text"])
        yes_button = tk.Button(run_popup, text="Yes", font=self.fonts["buttons"], bg="teal", fg="white",
                               command=self.start_fb)
        no_button = tk.Button(run_popup, text="Cancel", font=self.fonts["buttons"], bg="tomato2", fg="white",
                              command=run_popup.destroy)
        warning_label.grid(row=0, column=0)
        yes_button.grid(row=1, column=1)
        no_button.grid(row=1, column=2)

    def generate_config(self):
        config_files = []
        if not os.path.exists(os.path.join(self.script_dir, "configs")):
            os.chdir(self.script_dir)
            os.mkdir("configs")
        for filename in self.config_filenames[:2]:
            filename = os.path.join(self.script_dir, filename)
            config_files.append(open(filename, "w"))
        self.config_filenames[2] = os.path.join(self.script_dir, self.config_filenames[2])
        # only write running config if it doesn't already exist.
        if not os.path.exists(self.config_filenames[2]):
            with open(self.config_filenames[2], "w") as running_config:
                default_running_config = json.dumps(self.default_running_config, indent=4)
                running_config.write(default_running_config)
        # write cmd_config
        cmd_config = json.dumps(self.cmd_devices.as_dict(), indent=4)
        config_files[0].write(cmd_config)
        # write module_connections
        self.graph.add_node("meta", robot_id=self.id, key=self.key, rxn_name=self.rxn_name)
        graph_data = nx.readwrite.json_graph.node_link.node_link_data(self.graph)
        module_connections = json.dumps(graph_data, indent=4)
        config_files[1].write(module_connections)
        for file in config_files:
            file.close()
        self.write_message(f"Config files written to {self.script_dir}/configs")

    def load_configs(self):
        if self.config_cmd_flag:
            self.write_message("The command configuration has already been loaded")
        else:
            self.config_cmd_flag = True
            self.cmd_devices = CmdConfig()
            try:
                with open(self.config_filenames[0]) as file:
                    config = json.load(file)
                self.cmd_devices.load_existing(**config)
                self.write_message("Successfully loaded Commanduino configuration")
            except FileNotFoundError:
                self.write_message(f"File {self.config_filenames[0]} not found")
        if self.config_cxn_flag:
            self.write_message("The connections configuration has already been loaded")
        else:
            self.num_he_sens, self.num_syringes, self.num_valves = 0, 0, 0
            self.config_cxn_flag = True
            try:
                with open(self.config_filenames[1]) as file:
                    config = json.load(file)
                self.graph = nx.readwrite.json_graph.node_link_graph(config)
                self.graph_tmp = self.graph
                for node in self.graph.nodes.keys():
                    if "valve" in node:
                        self.num_valves += 1
                        self.num_he_sens += 1
                    elif "syringe" in node:
                        self.num_syringes += 1
                self.write_message("Successfully loaded connections configuration")
            except FileNotFoundError:
                self.write_message(f"File {self.config_filenames[1]} not found")

    def write_message(self, message):
        numlines = int(self.log.index("end - 1 line").split(".")[0])
        self.log["state"] = "normal"
        if numlines == 16:
            self.log.delete(1.0, 2.0)
        if self.log.index("end-1c") != "1.0":
            self.log.insert("end", "\n")
        lines = len(message)//79
        if lines >= 1:
            i = 0
            for i in range(lines):
                self.log.insert("end", message[i*79:(i+1)*79])
                self.log.insert("end", "\n")
            self.log.insert("end", message[(i+1)*79:])
        else:
            self.log.insert("end", message)
        self.log["state"] = "disabled"

    def start_fb(self):
        self.primary.destroy()
        directory = os.path.join(self.script_dir, "..")
        os.chdir(directory)
        subprocess.run(["python", "main.py"], shell=True)


if __name__ == "__main__":
    start_gui()