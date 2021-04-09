import tkinter as tk
import os
import json
from PIL import ImageTk, Image


class CmdConfig:
    def __init__(self):
        self.ios = []
        self.devices = {}

    def load_existing(self, ios, devices):
        self.ios = ios
        self.devices = devices

    def as_dict(self):
        return {'ios': self.ios, 'devices': self.devices}


class GraphConfig:
    def __init__(self):
        self.nodes = []
        self.links = []
        self.links_tmp = []
        self.valves = {}
        self.internalId = 0
        self.next_id = 0
        self.valve_ids = {}

    def load_existing(self, nodes, links):
        self.nodes = nodes
        self.links = links

    def add_valve(self, valve_name):
        self.valves[valve_name] = {"id": valve_name, "name": valve_name, 'mod_type': 'valve', 'class': 'SelectorValve'}
        self.add_node(self.valves[valve_name])

    def add_node(self, node):
        node['internalId'] = self.next_id
        self.internalId = self.next_id
        self.next_id += 1
        self.nodes.append(node)

    def add_link(self, source_name, source_id, target_name, target_id, target_port, dual):
        self.links_tmp.append({'id': None, 'sourceInternal': source_id, 'targetInternal': target_id,
                               'source': source_name, 'target': target_name, 'port': (source_id, target_port)})
        if dual:
            self.links_tmp.append({'id': None, 'sourceInternal': target_id, 'targetInternal': source_id,
                                   'source': target_name, 'target': source_name, 'port': (source_id, target_port)})

    def update_links(self):
        for link in self.links_tmp:
            link['id'] = self.next_id
            self.internalId = self.next_id
            self.next_id += 1
            self.links.append(link)

    @property
    def exists(self):
        if self.nodes:
            return True
        return False

    def as_dict(self):
        return {"nodes": self.nodes, "links": self.links}


class NodeConfig:
    def __init__(self):
        self.name = ''
        self.mod_type = ''
        self.class_type = ''
        self.valve_name = ''
        self.valve_id = None
        self.valve_flag = False
        self.flask_flag = False
        self.syringe_flag = False
        self.port_no = None
        self.add_params = []
        self.dual = None
        self.entries = []
        self.fields = []

    def as_dict(self):
        out_dict = {'id': self.name, 'name': self.name, 'mod_type': self.mod_type, 'class_type': self.class_type}
        out_dict.update(self.add_params)
        return out_dict

    def generate_flask(self):
        flask = ModConfig()
        raw_dict = self.as_dict()
        node_dict = {'name': self.name, 'mod_type': self.mod_type, 'class_type': self.class_type,
                     'mod_config': {'Contents': raw_dict['Contents'], 'Current volume': raw_dict['Current volume'],
                                    'Maximum volume': raw_dict['Maximum volume']}, 'devices': {}}
        flask.load_existing(**node_dict)
        return flask


class ModConfig:
    def __init__(self):
        self.name = 'name'
        self.mod_type = 'mod_type'
        self.class_type = 'class_type'
        self.mod_config = {}
        self.devices = {}

    def load_existing(self, name, mod_type, class_type, mod_config, devices):
        self.name = name
        self.mod_type = mod_type
        self.class_type = class_type
        self.mod_config = mod_config
        self.devices = devices

    @property
    def exists(self):
        if self.mod_config:
            return True
        return False

    def as_dict(self):
        return {self.name: {'name': self.name, 'mod_type': self.mod_type, "class_type": self.class_type, 'mod_config': self.mod_config,
                            'devices': self.devices}}


class SetupGUI:
    def __init__(self, primary):
        # todo select connections from graph file
        # todo add means to change syringe start position
        self.script_dir = os.path.dirname(__file__)
        self.primary = primary
        self.primary.title("FLuidic backbone setup")
        self.primary.configure(background='DarkOliveGreen1')
        self.fonts = {'buttons': ('Verdana', 12), 'labels': ('Verdana', 14), 'default': ('Verdana', 16),
                      'headings': ('Verdana', 16), 'text': ('Verdana', 10)}

        self.setup_frame = tk.Frame(self.primary, bg='grey', borderwidth=5)
        self.utilities_frame = tk.Frame(self.primary, bg='grey', borderwidth=2)
        self.log_frame = tk.Frame(self.primary)
        self.log = tk.Text(self.log_frame, state='disable', width=80, height=24, wrap='none', borderwidth=5)

        self.setup_label = tk.Label(self.primary, text='Fluidic backbone setup:', font=self.fonts['default'],
                                    padx=2, bg='white')
        self.utilities_label = tk.Label(self.primary, text='Utilities', font=self.fonts['default'], padx=2,
                                        bg='white')

        self.log_frame.grid(row=4, column=2, padx=5, pady=10)
        self.log.grid(row=0, column=0)
        self.setup_label.grid(row=2, column=2)
        self.utilities_label.grid(row=2, column=10)
        self.setup_frame.grid(row=3, column=2)
        self.utilities_frame.grid(row=3, column=10)

        self.text_temp = ''
        self.int_temp = 0
        self.com_ports = []
        self.cmd_devices = CmdConfig()
        self.modules = {}
        self.graph = GraphConfig()
        self.graph_tmp = GraphConfig()
        self.node_config = None
        self.num_syringes = 0
        self.num_valves = 0
        self.conf_syr = 0
        self.conf_valves = 0
        self.num_he_sens = 0
        self.config_flags = [False, False, False]
        self.es_options = {'X min': 3, 'X max': 2, 'Y min': 14, 'Y max': 15, 'Z min': 18, 'Z max': 19}
        self.motor_configs = {"default": {"steps_per_rev": 3200, "enabled_acceleration": False, "speed": 1000,
                                          "max_speed": 10000, "acceleration": 1000},
                              "cmd_default": {"enabled_acceleration": False, "speed": 1000, "max_speed": 10000,
                                              "acceleration": 1000}}
        self.motor_options = {'X': {'stepperX': {'cmd_id': 'STPX', 'enable_pin': 'ENX',
                                                 'device_config': self.motor_configs['default']}},
                              'Y': {'stepperY': {'cmd_id': 'STPY', 'enable_pin': 'ENY',
                                                 'device_config': self.motor_configs['default']}},
                              'Z': {'stepperZ': {'cmd_id': 'STPZ', 'enable_pin': 'ENZ',
                                                 'device_config': self.motor_configs['default']}},
                              'E0': {'stepperE0': {'cmd_id': 'STPE0', 'enable_pin': 'ENE0',
                                                   'device_config': self.motor_configs['default']}},
                              'E1': {'stepperE1': {'cmd_id': 'STPE1', 'enable_pin': 'ENE1',
                                                   'device_config': self.motor_configs['default']}}}
        self.pins = {'Analog Read 1 (A3)': 'AR1', 'Analog Read 2 (A4)': 'AR2'}
        self.used_motor_connectors = {}
        self.used_endstop_connectors = {}
        self.used_he_pins = []
        self.config_filenames = ['Configs/cmd_config.json', 'Configs/module_connections.json',
                                 'Configs/module_info.json']
        for file in self.config_filenames:
            file = os.path.join(self.script_dir, file)

        image_dir = os.path.join(self.script_dir, 'valve.png')
        self.valve_image = ImageTk.PhotoImage(Image.open(image_dir))

        self.simulation = False
        self.exit_flag = False
        self.init_setup_panel()
        self.init_utilities_panel()

    def init_setup_panel(self):
        def add_com_port():
            port = self.text_temp
            self.cmd_devices.ios.append({"port": port})
            self.write_message(f"Port {port} added")
            com_port_entry.delete(0, 'end')

        button_font = self.fonts['buttons']
        top_label = tk.Label(self.setup_frame, text='Setup', font=self.fonts['headings'], bg='white')
        com_port_label = tk.Label(self.setup_frame, text="Enter the communication port or TCP/IP address",
                                  font=self.fonts['labels'], bg='white')
        val_text = self.primary.register(self.validate_text)
        com_frame = tk.Frame(self.setup_frame, bg='grey', pady=4)
        com_port_entry = tk.Entry(com_frame, validate='key', validatecommand=(val_text, '%P'),
                                  bg='white', fg='black', width=25)
        com_port_button = tk.Button(com_frame, text='Accept', font=button_font, bg='lawn green',
                                    fg='black', command=add_com_port)
        mod_frame = tk.Frame(self.setup_frame, bg='grey', pady=4)

        con_label = tk.Label(self.setup_frame, text='Backbone modules and connections setup', font=self.fonts['labels'],
                             bg='white')
        con_button = tk.Button(self.setup_frame, text='Configure modules', font=button_font, bg='LemonChiffon2',
                               fg='black', command=self.graph_setup)
        gen_button = tk.Button(self.setup_frame, text='Create config', font=button_font, bg='lawn green',
                               fg='black', command=self.generate_config)

        top_label.grid(row=0, column=1)
        com_port_label.grid(row=1, column=1)
        com_frame.grid(row=2, column=1)
        com_port_entry.grid(row=0, column=0, padx=4)
        com_port_button.grid(row=0, column=1, padx=4)
        mod_frame.grid(row=4, column=1)
        con_label.grid(row=5, column=1)
        con_button.grid(row=6, column=1, pady=4)
        gen_button.grid(row=0, column=3)

    def init_utilities_panel(self):
        button_font = self.fonts['buttons']
        run_fb_button = tk.Button(self.utilities_frame, text='Run Fluidic Backbone', font=self.fonts['buttons'],
                                  bg='DeepSkyBlue', fg='black', command=self.run_fb_menu)
        lc_butt = tk.Button(self.utilities_frame, text='Load existing commanduino config', font=button_font,
                            bg='LemonChiffon2', fg='black', command=lambda: self.load_configs(1, 0, 0))
        lg_butt = tk.Button(self.utilities_frame, text='Load existing graph config', font=button_font,
                            bg='LemonChiffon2', fg='black', command=lambda: self.load_configs(0, 1, 0))
        lm_butt = tk.Button(self.utilities_frame, text='Load existing module config', font=button_font,
                            bg='LemonChiffon2', fg='black', command=lambda: self.load_configs(0, 0, 1))
        lc_butt.grid(row=1, column=0, padx=4, pady=4)
        lg_butt.grid(row=2, column=0, padx=4, pady=4)
        lm_butt.grid(row=3, column=0, padx=4, pady=4)
        run_fb_button.grid(row=4, column=0, padx=4, pady=10)

    def graph_setup(self):
        def accept():
            if self.conf_valves > 0 and self.conf_syr > 0:
                self.config_flags[1] = False
                self.graph_tmp.update_links()
                self.graph = self.graph_tmp
                graph_setup.destroy()
            else:
                self.write_message("Required to configure at least one valve and syringe")

        def populate_menus(frame, valve_no, count, port, col, span=False):
            col_span = 1
            if span:
                col_span = 2
            row = count * 2
            port_var = tk.StringVar(frame)
            port_var.set('')
            port_button = tk.Button(frame, text=f'Configure port {port}', bg='LightBlue3', fg='black')
            port_button.configure(command=lambda v=valve_no,
                                  pv=port_var, pn=port, pb=port_button: port_menu_start(v, pv, pn, pb))
            port_button.grid(row=row, column=col, columnspan=col_span)
            port_om = tk.OptionMenu(frame, port_var, *options)
            port_om.grid(row=row + 1, column=col, columnspan=col_span)

        if self.num_valves == 0 or self.num_syringes == 0:
            if self.num_valves == 0:
                valves_query = tk.Toplevel(self.primary)
                valves_query.attributes('-topmost', 'true')
                q_label = tk.Label(valves_query, text='How many valves are attached to the backbone?')
                validate_valves = valves_query.register(self.validate_int)
                q_entry = tk.Entry(valves_query, validate='key', validatecommand=(validate_valves, '%P'))
                ok_button = tk.Button(valves_query, text='Accept', bg='lawn green',
                                      command=lambda: self.add_mod('sv', valves_query))
                cancel_button = tk.Button(valves_query, text='Cancel', bg='tomato2', command=valves_query.destroy)

                q_label.grid(row=0, column=1)
                q_entry.grid(row=1, column=1)
                ok_button.grid(row=2, column=0)
                cancel_button.grid(row=2, column=2)

            if self.num_syringes == 0:
                syringe_query = tk.Toplevel(self.primary)
                syringe_query.attributes('-topmost', 'true')
                q_label = tk.Label(syringe_query, text="How many syringes are attached to the backbone?")
                validate_syr = syringe_query.register(self.validate_int)
                q_entry = tk.Entry(syringe_query, validate='key', validatecommand=(validate_syr, '%P'))
                ok_button = tk.Button(syringe_query, text='Accept', bg='lawn green',
                                      command=lambda: self.add_mod('sp', syringe_query))
                cancel_button = tk.Button(syringe_query, text='Cancel', bg='tomato2', command=syringe_query.destroy)

                q_label.grid(row=0, column=1)
                q_entry.grid(row=1, column=1)
                ok_button.grid(row=2, column=0)
                cancel_button.grid(row=2, column=2)
        else:
            graph_setup = tk.Toplevel(self.primary)
            graph_setup.title('Backbone connections setup')
            self.graph_tmp = GraphConfig()
            options = ['reactor', 'syringe', 'flask', 'waste', 'filter']
            for i in range(0, self.num_valves):
                valve_name = f'valve{i + 1}'
                self.graph_tmp.add_valve(valve_name)
                valve_frame = tk.Frame(graph_setup)
                valve_frame.grid(row=1, column=i)
                top_label = tk.Label(valve_frame, text=f'Valve {i + 1}', font=self.fonts['default'])
                top_label.grid(row=0, column=1)
                left_ports = tk.Frame(valve_frame)
                img_frame = tk.Frame(valve_frame)
                right_ports = tk.Frame(valve_frame)
                img_frame.grid(row=1, column=1)
                left_ports.grid(row=1, column=0)
                right_ports.grid(row=1, column=2)

                for j, k in enumerate(range(6, 10)):
                    populate_menus(left_ports, valve_no=i, count=j, port=k, col=0)

                image = tk.Label(img_frame, image=self.valve_image)
                image.grid(row=3, column=0, columnspan=2)
                populate_menus(img_frame, valve_no=i, count=0, port=5, col=0)
                populate_menus(img_frame, valve_no=i, count=0, port=-1, col=1)
                populate_menus(img_frame, valve_no=i, count=3, port=0, col=0, span=True)

                for j, k in enumerate(range(4, 0, -1)):
                    populate_menus(right_ports, valve_no=i, count=j, port=k, col=2)

                valve_button = tk.Button(img_frame, text=f'Valve {i + 1} setup', font=self.fonts['buttons'],
                                         bg='LightBlue3',
                                         fg='black')
                valve_button.configure(command=lambda: self.valve_setup(valve_button))
                valve_button.grid(row=9, column=0, columnspan=2)

            options_frame = tk.Frame(graph_setup, bg='grey', borderwidth=5)
            options_frame.grid(row=1, column=i + 1)
            accept_butt = tk.Button(graph_setup, text='Accept', bg='lawn green', command=accept)
            cancel_butt = tk.Button(graph_setup, text='Cancel', bg='tomato2', command=graph_setup.destroy)
            accept_butt.grid(row=2, column=1)
            cancel_butt.grid(row=2, column=2)

            def port_menu_start(valve_no, p_var, port_no, port_button):
                def accept_p(button):
                    if not node_config.name:
                        node_config.name = node_config.entries[0][1].get()
                    for entry in node_config.entries:
                        field = entry[0]
                        words = field.split(' ')
                        if len(words) > 2:
                            field = words[0] + " " + words[1]
                        config = entry[1].get()
                        node_config.add_params.append((field, config))
                    if not node_config.valve_flag:
                        node_dict = node_config.as_dict()
                        self.graph_tmp.add_node(node_dict)
                        target_id = self.graph_tmp.internalId
                        if node_config.mod_type == 'flask':
                            flask = node_config.generate_flask()
                            self.modules[flask.name] = flask
                    else:
                        target_id = self.graph_tmp.valves[node_config.name]['internalId']
                    self.graph_tmp.add_link(source_name=node_config.valve_name, source_id=node_config.valve_id,
                                            target_name=node_config.name, target_id=target_id,
                                            target_port=node_config.port_no, dual=node_config.dual)
                    button.configure(bg='lawn green')
                    delete_fields(options_frame)

                def generate_fields(field_list, config):
                    # todo add validation to volume entries
                    title = tk.Label(options_frame, text=f'Configure port {config.port_no}',
                                     font=self.fonts['headings'])
                    title.grid(row=0, column=0, columnspan=2)
                    offset = 1
                    if config.syringe_flag:
                        offset = 2
                        label = tk.Label(options_frame, text=f'syringe{self.conf_syr + 1}')
                        label.grid(row=1, column=0, columnspan=2)
                    for cnt, field in enumerate(field_list):
                        label = tk.Label(options_frame, text=field)
                        label.grid(row=cnt + offset, column=0)
                        entry = tk.Entry(options_frame)
                        entry.grid(row=cnt + offset, column=1)
                        config.entries.append((field, entry))
                    if config.syringe_flag:
                        accept_p_butt = tk.Button(options_frame, text='Accept', bg='lawn green', state='disabled',
                                                  command=lambda: accept_p(port_button))
                        syringe_button = tk.Button(options_frame, text='Syringe motor configuration',
                                                   font=self.fonts['buttons'],
                                                   bg='LemonChiffon2',
                                                   fg='black', command=lambda: self.syringe_setup(accept_p_butt))
                        syringe_button.grid(row=cnt + offset + 1, column=0, columnspan=2)

                    else:
                        accept_p_butt = tk.Button(options_frame, text='Accept', bg='lawn green',
                                                  command=lambda: accept_p(port_button))
                    accept_p_butt.grid(row=cnt + offset + 2, column=0)

                def delete_fields(o_frame):
                    for widget in o_frame.winfo_children():
                        widget.destroy()

                variable = p_var.get()
                if variable != '':
                    node_config = NodeConfig()
                    fields = ["Name", "Current volume in ml", "Maximum volume in ml"]
                    if variable == 'flask':
                        node_config.mod_type = 'flask'
                        node_config.class_type = 'FBFlask'
                        fields += ['Contents']
                        node_config.dual = True
                        node_config.flask_flag = True
                    elif variable == 'waste':
                        node_config.mod_type = 'waste'
                        node_config.class_type = 'FBFlask'
                        node_config.dual = False
                    elif variable == 'filter':
                        node_config.mod_type = 'filter'
                        node_config.class_type = 'FBFlask'
                        fields += ["Dead volume in ml"]
                        node_config.dual = False
                    elif variable == 'syringe':
                        node_config.name = f"syringe{self.conf_syr + 1}"
                        node_config.mod_type = 'syringe'
                        node_config.class_type = 'SyringePump'
                        fields += ['Minimum volume in ml', 'Contents']
                        fields.pop(0)
                        node_config.syringe_flag = True
                        node_config.dual = True
                    elif 'valve' in variable:
                        node_config.name = f"syringe{self.conf_valves + 1}"
                        node_config.mod_type = 'valve'
                        node_config.class_type = 'SelectorValve'
                        node_config.valve_flag = True
                        node_config.dual = False
                    node_config.valve_name = f'valve{valve_no + 1}'
                    node_config.valve_id = valve_no
                    node_config.port_no = port_no
                    generate_fields(fields, node_config)

    def add_mod(self, mod_type, popup):
        if mod_type == 'sp':
            self.num_syringes = self.int_temp
        elif mod_type == 'sv':
            self.num_valves = self.int_temp
        popup.destroy()
        if self.num_syringes > 0 and self.num_valves > 0:
            self.graph_setup()

    def syringe_setup(self, button):
        def accept():
            motor_cxn = motor_connector.get()
            endstop = endstop_connector.get()
            select_new = False
            if motor_cxn and endstop:
                if motor_cxn in self.used_motor_connectors.keys():
                    select_new = True
                    self.write_message(
                        f"That motor connector is already used by {self.used_motor_connectors[motor_cxn]}")
                if endstop in self.used_endstop_connectors.keys():
                    select_new = True
                    self.write_message(
                        f'That endstop connector is already used by {self.used_endstop_connectors[endstop]}')
                if not select_new:
                    self.conf_syr += 1
                    syringe_name = f'syringe{self.conf_syr}'
                    self.modules[syringe_name] = ModConfig()
                    module = self.modules[syringe_name]
                    stepper_name = f'stepper{motor_cxn}'
                    self.used_motor_connectors[motor_cxn] = syringe_name
                    self.used_endstop_connectors[endstop] = syringe_name
                    module.name = syringe_name
                    module.mod_type = 'syringe'
                    module.class_type = 'SyringePump'
                    module.mod_config = {'screw_pitch': 8, 'linear_stepper': True}
                    self.setup_motor(syringe_name, stepper_name, motor_cxn)
                    self.config_flags[0], self.config_flags[2] = False, False
                    button.configure(state='normal')
                    syringe_setup.destroy()
            else:
                if not motor_cxn:
                    self.write_message('Please select a motor connector')
                if not endstop:
                    self.write_message('Please select an endstop connector')

        syringe_setup = tk.Toplevel(self.primary)
        syringe_setup.title('Syringe setup')
        font = self.fonts['default']
        motor_connector = tk.StringVar(syringe_setup)
        endstop_connector = tk.StringVar(syringe_setup)
        motor_connection_label = tk.Label(syringe_setup, text='Which motor connector is used for this syringe',
                                          font=font)
        motor_connection_label.grid(row=0, column=0)
        i = 1
        options = self.motor_options.keys()
        selected = self.used_motor_connectors.keys()
        for motor in options:
            tk.Radiobutton(syringe_setup, text=motor, variable=motor_connector, value=motor).grid(row=i, column=0)
            i += 1
        motor_connector.set(self.find_unselected(options, selected))
        endstop_label = tk.Label(syringe_setup, text='Which endstop connection is used for this syringe?', font=font)
        endstop_label.grid(row=7, column=0)
        i = 8
        options = self.es_options.keys()
        selected = self.used_endstop_connectors.keys()
        for option in options:
            tk.Radiobutton(syringe_setup, text=option, variable=endstop_connector, value=option).grid(row=i, column=0)
            i += 1
        endstop_connector.set(self.find_unselected(options, selected))

        accept_button = tk.Button(syringe_setup, text='Accept', fg='black', bg='lawn green', command=accept)
        cancel_button = tk.Button(syringe_setup, text='Cancel', fg='black', bg='tomato2', command=syringe_setup.destroy)
        accept_button.grid(row=i, column=0)
        cancel_button.grid(row=i, column=1)

    def valve_setup(self, valve_button):
        def accept(button):
            motor_cxn = motor_connector.get()
            try:
                pin = hall_connector.get()
                gear = geared_motor.get()
                hall_sensor = self.pins[pin]
            except KeyError:
                self.write_message('Please select a pin for the hall-effect sensor')
            else:
                if motor_cxn:
                    if motor_cxn in self.used_motor_connectors.keys():
                        self.write_message(
                            f"That motor connector is already used by {self.used_motor_connectors[motor_cxn]}")
                    else:
                        self.conf_valves += 1
                        self.num_he_sens += 1
                        valve_name = f'valve{self.conf_valves}'
                        self.modules[valve_name] = ModConfig()
                        module = self.modules[valve_name]
                        stepper_name = f'stepper{motor_cxn}'
                        he_sens_name = f'he_sens{self.num_he_sens}'
                        self.used_motor_connectors[motor_cxn] = valve_name
                        self.used_he_pins.append(pin)
                        module.name = valve_name
                        module.mod_type = 'valve'
                        module.class_type = 'SelectorValve'
                        if gear == '':
                            gear = 'Direct drive'
                        module.mod_config = {'ports': 10, "linear_stepper": False, 'gear': gear}
                        self.setup_motor(valve_name, stepper_name, motor_cxn)
                        module.devices['he_sens'] = {'name': he_sens_name, 'cmd_id': hall_sensor, 'device_config': {}}
                        self.cmd_devices.devices[hall_sensor] = {'command_id': hall_sensor}
                        self.config_flags[0], self.config_flags[2] = False, False
                        button.configure(bg='lawn green')
                        valve_setup.destroy()

        valve_setup = tk.Toplevel(self.primary)
        valve_setup.title('Valve setup')
        font = self.fonts['default']
        motor_connector = tk.StringVar(valve_setup)
        hall_connector = tk.StringVar(valve_setup)
        geared_motor = tk.StringVar(valve_setup)
        motor_text = 'Which motor connector is used for this valve?'
        motor_connection_label = tk.Label(valve_setup, text=motor_text, font=font)
        i = 1
        options = self.motor_options.keys()
        selected = self.used_motor_connectors.keys()
        for motor_cn in options:
            tk.Radiobutton(valve_setup, text=motor_cn, variable=motor_connector, value=motor_cn).grid(row=i, column=0)
            i += 1
        motor_connector.set(self.find_unselected(options, selected))
        hall_sensor_label = tk.Label(valve_setup, text='Which pin is the hall sensor plugged into?', font=font)
        hall_options = list(self.pins.keys())
        pin_to_remove = None
        for j in range(0, len(hall_options)):
            if hall_options[j] in self.used_he_pins:
                pin_to_remove = j
        if pin_to_remove is not None:
            hall_options.pop(pin_to_remove)
        hall_sensor_selector = tk.OptionMenu(valve_setup, hall_connector, *hall_options)

        gear_options = ['Direct drive', '1.5:1', '2:1', '3:1']
        geared_motor.set('')
        gear_label = tk.Label(valve_setup, text='Gear options:', font=font)
        gear_selector = tk.OptionMenu(valve_setup, geared_motor, *gear_options)

        accept_button = tk.Button(valve_setup, text='Accept', fg='black', bg='lawn green',
                                  command=lambda: accept(valve_button))
        cancel_button = tk.Button(valve_setup, text='Cancel', fg='black', bg='tomato2',
                                  command=valve_setup.destroy)

        motor_connection_label.grid(row=0, column=0)
        hall_sensor_label.grid(row=7, column=0)
        hall_sensor_selector.grid(row=8, column=0)
        gear_label.grid(row=9)
        gear_selector.grid(row=10)
        accept_button.grid(row=16, column=0)
        cancel_button.grid(row=16, column=1)

    def setup_motor(self, name, stepper_name, motor_cn):
        motor_config = {'name': stepper_name}
        motor_config.update(self.motor_options[motor_cn][stepper_name])
        mod_info_device = {'stepper': motor_config}
        self.modules[name].devices.update(mod_info_device)
        self.cmd_devices.devices[stepper_name] = {'command_id': motor_config['cmd_id'],
                                                  'config': self.motor_configs['default']}
        enable_pin = motor_config['enable_pin']
        self.cmd_devices.devices[enable_pin] = {'command_id': enable_pin}

    def validate_text(self, new_text):
        if not new_text:
            self.text_temp = ''
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
    def find_unselected(possible_options, selected_options):
        options = list(possible_options)
        selected = list(selected_options)
        for option in options:
            if option not in selected:
                return option

    def run_fb_menu(self):
        run_popup = tk.Toplevel(self.primary)
        run_popup.title('Run Fluidic Backbone')
        warning_label = tk.Label(run_popup,
                                 text='Have you finished configuring the system? Selecting yes will use configuration '
                                      'stored in configs folder.',
                                 font=self.fonts['text'])
        yes_button = tk.Button(run_popup, text='Yes', font=self.fonts['buttons'], bg='teal', fg='white',
                               command=self.start_fb)
        no_button = tk.Button(run_popup, text='Cancel', font=self.fonts['buttons'], bg='tomato2', fg='white',
                              command=run_popup.destroy)
        warning_label.grid(row=0, column=0)
        yes_button.grid(row=1, column=1)
        no_button.grid(row=1, column=2)

    def generate_config(self):
        config_files = []
        for filename in self.config_filenames:
            config_files.append(open(filename, 'w'))
        cmd_config = json.dumps(self.cmd_devices.as_dict(), indent=4)
        config_files[0].write(cmd_config)
        module_connections = json.dumps(self.graph.as_dict(), indent=4)
        config_files[1].write(module_connections)
        modules = {}
        for k in self.modules:
            modules.update(self.modules[k].as_dict())
        module_config = json.dumps(modules, indent=4)
        config_files[2].write(module_config)
        for file in config_files:
            file.close()
        self.write_message("Config files written")

    def load_configs(self, cmd_cnf, md_cxn, md_cnf):
        if cmd_cnf:
            if self.config_flags[0]:
                self.write_message("The command configuration has already been loaded")
            else:
                self.config_flags[0] = True
                self.cmd_devices = CmdConfig()
                try:
                    with open(self.config_filenames[0]) as file:
                        config = json.load(file)
                    self.cmd_devices.load_existing(**config)
                    self.write_message('Successfully loaded Commanduino configuration')
                except FileNotFoundError:
                    self.write_message(f'File {self.config_filenames[0]} not found')

        if md_cxn:
            if self.config_flags[1]:
                self.write_message("The connections configuration has already been loaded")
            else:
                self.config_flags[1] = True
                self.graph = GraphConfig()
                try:
                    with open(self.config_filenames[1]) as file:
                        config = json.load(file)
                    self.graph.load_existing(**config)
                    self.write_message('Successfully loaded connections configuration')
                except FileNotFoundError:
                    self.write_message(f'File {self.config_filenames[1]} not found')
        if md_cnf:
            if self.config_flags[2]:
                self.write_message("The module configuration has already been loaded")
            else:
                self.config_flags[2] = True
                self.modules = {}
                self.num_he_sens, self.num_syringes, self.num_valves = 0, 0, 0
                try:
                    with open(self.config_filenames[2]) as file:
                        config = json.load(file)
                    for k in config:
                        name = config[k]['name']
                        if 'syringe' in name:
                            self.num_syringes += 1
                        elif 'valve' in name:
                            self.num_valves += 1
                        elif 'he_sens' in name:
                            self.num_he_sens += 1
                        new_mod = ModConfig()
                        new_mod.load_existing(**config[name])
                        self.modules[name] = new_mod
                    self.write_message("Successfully loaded module configuration")
                except FileNotFoundError:
                    self.write_message(f'File {self.config_filenames[2]} not found')

    def write_message(self, message):
        numlines = int(self.log.index('end - 1 line').split('.')[0])
        self.log['state'] = 'normal'
        if numlines == 24:
            self.log.delete(1.0, 2.0)
        if self.log.index('end-1c') != '1.0':
            self.log.insert('end', '\n')
        self.log.insert('end', message)
        self.log['state'] = 'disabled'

    def start_fb(self):
        self.primary.destroy()
        os.system('python Fluidic_backbone_GUI.py')


if __name__ == '__main__':
    root = tk.Tk()
    program = SetupGUI(root)
    root.mainloop()
