import sys
import os
import logging
import json
import networkx as nx
import datetime
import time
import math
from networkx.readwrite.json_graph import node_link_graph
from queue import Queue
from threading import Thread, Lock
import commanduino
import UJ_FB.fluidic_backbone_gui as fluidic_backbone_gui
import UJ_FB.web_listener as web_listener
from UJ_FB.modules import syringepump, selectorvalve, reactor, modules, fluidstorage
import UJ_FB.fbexceptions as fbexceptions


def json_loader(root, fp, object_hook=None):
    fp = os.path.join(root, fp)
    try:
        with open(fp) as file:
            return json.load(file, object_hook=object_hook)
    except (FileNotFoundError, json.decoder.JSONDecodeError) as e:
        raise fbexceptions.FBConfigurationError(f"The JSON provided {fp} is invalid. \n {e}")


def load_graph(graph_config):
    graph = node_link_graph(graph_config, directed=True, multigraph=True)
    return graph


def object_hook_int(obj):
    """
    :param obj: dictionary converted from JSON
    :return: dictionary of JSON data with integers formatted
    """
    output = {}
    for k, v in obj.items():
        key = k
        if isinstance(k, str):
            try:
                key = int(k)
            except ValueError:
                pass
        output[key] = v
    return output


def get_log_location():
    pass


class Manager(Thread):
    """
    Class for managing the fluidic backbone robot. Keeps track of all modules and implements high-level methods for
    tasks involving multiple modules. Uses a queue to hold command dictionaries and interprets these to control modules
    """
    def __init__(self, gui=True, stdout_log=False, simulation=False, web_enabled=False):
        Thread.__init__(self)
        # get absolute directory of script
        self.script_dir = os.path.dirname(__file__)
        cm_config = os.path.join(self.script_dir, "configs/cmd_config.json")
        self.cmd_mng = commanduino.CommandManager.from_configfile(cm_config, simulation)
        graph_config = json_loader(self.script_dir, "configs/module_connections.json")
        self.graph = load_graph(graph_config)
        self.key = self.graph.nodes["meta"]["key"]
        self.id = self.graph.nodes["meta"]["robot_id"]
        self.prev_run_config = json_loader(self.script_dir, "configs/running_config.json", object_hook=object_hook_int)
        self.name = "Manager" + self.id
        self.logger = logging.getLogger(self.id)
        self.q = Queue()
        self.pipeline = Queue()
        self.error_queue = Queue()
        # list to hold current Task objects.
        self.tasks = []
        self.serial_lock = Lock()
        self.interrupt_lock = Lock()
        self.pause_after_rxn = False
        self.user_wait_flag = False
        self.waiting = False
        self.interrupt = False
        self.exit_flag = False
        self.stop_flag = False
        self.pause_flag = False
        self.paused = False
        self.ready = True
        self.execute = False
        self.reaction_ready = False
        self.reaction_name = ""
        self.reaction_id = None
        self.error = False
        self.error_start = None
        self.error_flag = False
        self.valid_nodes = []
        self.modules = {"valves": {}, "syringes": {}, "reactors": {}, "flasks": {}, "cameras": {}, "storage": {}}
        self.valves = self.modules["valves"]
        self.num_valves = 0
        self.syringes = self.modules["syringes"]
        self.reactors = self.modules["reactors"]
        self.flasks = self.modules["flasks"]
        self.cameras = self.modules["cameras"]
        self.storage = self.modules["storage"]
        self.gui_main = None
        self.setup_modules()
        self.default_fr = 10000
        self.default_flush_fr = 20000
        self.init_syringes()
        self.listener = web_listener.WebListener(self, self.id, self.key)
        self.web_enabled = web_enabled
        self.rc_changes = False
        self.write_running_config("configs/running_config.json")
        self.xdl = ""
        if stdout_log:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.INFO)
            self.logger.addHandler(handler)
        if web_enabled:
            self.listener.test_connection()
        self.start()
        if gui:
            self.gui_main = fluidic_backbone_gui.FluidicBackboneUI(self)
            self.gui_main.mainloop()

    def update_url(self, url):
        self.listener.update_url(url)

    def write_log(self, message, level=logging.INFO):
        if self.gui_main is not None:
            if level > 9:
                self.gui_main.queue.put(("log", message))
        message = datetime.datetime.today().strftime("%Y-%m-%dT%H:%M") + f"({self.id})" + message
        if level > 49:
            self.logger.critical(message)
        elif level > 39:
            self.logger.error(message)
        elif level > 29:
            self.logger.warning(message)
        elif level > 19:
            self.logger.info(message)
        elif level > 9:
            self.logger.info(message)

    def write_running_config(self, fp):
        fp = os.path.join(self.script_dir, fp)
        with open(fp, "w+") as rc_file:
            running_config = json.dumps(self.prev_run_config, indent=4)
            rc_file.write(running_config)
        self.rc_changes = False

    def setup_modules(self):
        """
        Reads the graph, appending node data to the required objects.
        """
        syringes = 0
        g = self.graph
        valves_list = []
        for n in list(g.nodes):
            if g.degree[n] < 1:
                self.write_log(f"Node {n} is not connected to the system!", level=logging.WARNING)
            else:
                name = g.nodes[n]["name"]
                mod_type = g.nodes[n]["mod_type"]
                self.valid_nodes.append(name)
                if "syringe_pump" in mod_type:
                    syringes += 1
                    self.syringes[name] = syringepump.SyringePump(name, g.nodes[name], self.cmd_mng, self)
                    syringe = self.syringes[name]
                    node = g.nodes[n]
                    node["object"] = syringe
                    syringe.set_max_volume(node["mod_config"]["max_volume"])
                    syringe.contents[1][0] = node["mod_config"]["contents"]
                    syringe.contents[1][1] = 0
                    syringe.set_pos(0)
                elif "selector_valve" in mod_type:
                    self.num_valves += 1
                    self.valves[name] = selectorvalve.SelectorValve(name, g.nodes[name], self.cmd_mng, self)
                    valves_list.append(n)
                    g.nodes[n]["object"] = self.valves[name]
                elif "flask" in mod_type or "waste" in mod_type:
                    self.flasks[name] = modules.FBFlask(name, g.nodes[n], self.cmd_mng, self)
                    g.nodes[n]["object"] = self.flasks[name]
                elif "reactor" in mod_type:
                    self.reactors[name] = reactor.Reactor(name, g.nodes[n], self.cmd_mng, self)
                    g.nodes[n]["object"] = self.reactors[name]
                elif "storage" in mod_type:
                    self.storage[name] = fluidstorage.FluidStorage(name, g.nodes[n], self.cmd_mng, self)
                    g.nodes[n]["object"] = self.storage[name]
        if syringes == 0:
            self.write_log("No pumps configured", level=logging.WARNING)
            time.sleep(2)
            self.interrupt = True
            self.exit_flag = True
        for valve in valves_list:
            name = g.nodes[valve]["name"]
            g.nodes[valve]["object"] = self.valves[name]
            for node_name in g.adj[valve]:
                port = g.adj[valve][node_name][0]["port"][1]
                self.valves[name].ports[port] = g.nodes[node_name]["object"]
                if "valve" in node_name:
                    self.valves[name].adj_valves.append((node_name, port))
            syringe = self.valves[name].ports[-1]
            self.valves[name].syringe = syringe
            syringe.valve = self.valves[name]
        self.reaction_name = self.graph.nodes["meta"].get("rxn_name")
        if self.reaction_name:
            self.write_log(f"Robot {self.id} is configured for reaction {self.reaction_name}")

    def init_syringes(self):
        """
            Initialises the syringes by moving them to their endstop, dispensing contents into the nearest
            waste container. If no waste container is found,  prints a message warning the user.
        """
        for valve in self.valves:
            # home and prepare valve for running
            self.valves[valve].init_valve()
            syringe = self.valves[valve].syringe
            # check if syringe needs to be homed
            if not syringe.stepper.check_endstop():
                # search for waste containers looking for shortest path
                waste_containers = [item for item in list(self.graph.nodes) if "waste" in item.lower()]
                if not waste_containers:
                    message = f"No waste containers are attached. Please manually empty {syringe.name} using the GUI"
                    self.write_log(message, level=logging.WARNING)
                    continue
                shortest_waste_path = []
                for waste in waste_containers:
                    path_gen = nx.algorithms.simple_paths.all_simple_paths(self.graph, syringe.name, waste)
                    path_list = [p for p in path_gen]
                    if len(path_list[0]) < len(shortest_waste_path) or not shortest_waste_path:
                        shortest_waste_path = path_list[0]
                # Align valves without dispensing much liquid
                self.move_fluid(source=syringe.name, target=shortest_waste_path[-1], volume=0.1, flow_rate=10000,
                                init_move=True)
                # with valves at waste can move to 0
                self.add_to_queue(Manager.generate_cmd_dict("syringe", syringe.name, "home", {"wait": True}))
            self.start_queue()
    
    def reload_graph(self):
        graph_config = json_loader(self.script_dir, "configs/module_connections.json")
        self.graph = load_graph(graph_config)
        self.setup_modules()

    def run(self):
        """
        This is the primary loop of the program. This loop monitors for errors or interrupts, dispatches tasks,
         updates the server and has logic to handle pauses.
        """
        rxn_last_check = time.time()
        heat_update_time = time.time()
        while not self.exit_flag:
            self.check_task_completion()
            # interrupt lock used to synchronise access to pause, stop, and exit flags
            with self.interrupt_lock:
                pause_flag = self.pause_flag
                error = self.error
                if self.web_enabled:
                    execute = self.listener.update_execution()
                    self.execute = execute
                else:
                    execute = self.execute
                # We have received a command to stop or start execution
                if not execute and execute is not None:
                    # if not ready then we must pause the current execution
                    if not self.ready:
                        self.pause_flag = True
                if self.interrupt:
                    if self.exit_flag:
                        break
                    elif self.pause_flag and not self.paused:
                        self.pause_all()
                    elif self.stop_flag:
                        self.stop_all()
                    elif not self.pause_flag and self.paused:
                        self.resume()
                    self.interrupt = False
            if self.q.empty() and not self.tasks:
                self.ready = True
                self.ensure_reactors_disabled()
                if self.web_enabled:
                    self.listener.update_status(ready=self.ready)
                if not self.reaction_ready:
                    # log reaction completion once
                    if self.reaction_name:
                        self.write_log(f"Completed {self.reaction_name}, id {self.reaction_id}", level=logging.INFO)
                        if self.reaction_id:
                            self.listener.update_status(True, reaction_complete=True)
                        self.reaction_name = ""
                        self.reaction_id = None
                        self.home_all_valves()
                    # Attempt to request reaction from server
                    if self.web_enabled:
                        if time.time() - rxn_last_check > 10:
                            rxn_last_check = time.time()
                            if self.listener.request_reaction():
                                self.write_log(f"Prepared to run {self.reaction_name} reaction.", level=logging.INFO)
                    time.sleep(2)
                # a reaction has been queued
                else:
                    if execute and not self.pause_after_rxn:
                        self.start_queue()
                        self.write_log(f"Started running {self.reaction_name}, id {self.reaction_id}",
                                       level=logging.INFO)
                        self.reaction_ready = False
                        self.ready = False
                        self.listener.update_status(False)
                        continue
            # execution ongoing
            if error:
                if self.web_enabled:
                    self.listener.update_status(self.ready, error=True)
                elif time.time() - self.error_start > 300:
                    self.ensure_reactors_disabled()
            if self.execute != execute:
                if self.gui_main is not None:
                    self.gui_main.update_execution(execute)
            if not pause_flag:
                # waiting for task completion
                if self.waiting:
                    if not self.tasks:
                        with self.interrupt_lock:
                            self.waiting = False
                #  move on to next queued item
                elif not self.q.empty():
                    command_dict = self.q.get(block=False)
                    if not self.command_module(command_dict):
                        message = f"Failed to add command {command_dict['command']} for {command_dict['module_name']}"
                        self.write_log(message, level=logging.ERROR)
            elif self.error and not self.error_queue.empty():
                command_dict = self.error_queue.get(block=False)
                self.command_module(command_dict)
            if self.gui_main is not None and time.time() - heat_update_time > 5:
                heat_update_time = time.time()
                for r in self.reactors:
                    r = self.reactors[r]
                    temp = round(r.cur_temp)
                    if temp < 0:
                        temp = "-"
                    self.gui_main.queue.put(("temp", (r.name, temp)))
            if self.rc_changes:
                self.write_running_config("configs\\running_config.json")
        self.exit_program()

    def add_to_queue(self, commands, queue=None):
        """
        Adds a command(s) to the queue or pipeline.
        """
        if queue is None:
            queue = self.pipeline
        for command in commands:
            queue.put(command)

    def echo_queue(self):
        pipeline = []
        while not self.pipeline.empty():
            command_dict = self.pipeline.get(block=False)
            pipeline.append(command_dict)
        self.add_to_queue(pipeline)
        return pipeline

    def export_queue(self):
        output = {"pipeline": list(self.pipeline.queue)}
        export_queue = json.dumps(output, indent=4)
        pipeline_path = os.path.join(self.script_dir, "configs/Pipeline.json")
        file = open(pipeline_path, "w+")
        file.write(export_queue)
        file.close()

    def import_queue(self, file, overwrite=False):
        """
        Imports a saved queue from a JSON file.
        """
        file = os.path.join(self.script_dir, file)
        try:
            with open(file) as queue_file:
                queue_list = json.load(queue_file)["pipeline"]
        except json.decoder.JSONDecodeError:
            self.write_log("That is not a valid JSON file", level=logging.WARNING)
            return False
        if overwrite:
            self.pipeline.queue.clear()
        protocol = queue_list.get("protocol")
        if protocol:
            self.xdl = protocol
        if queue_list.get("pipeline"):
            self.add_to_queue(queue_list)
        else:
            if not self.listener.load_xdl(self.xdl, is_file=False):
                return False

    def start_queue(self):
        """
        Begins execution of the queued actions
        """
        with self.interrupt_lock:
            self.pause_flag = True
            self.interrupt = True
        while not self.pipeline.empty():
            command_dict = self.pipeline.get(block=False)
            self.q.put(command_dict)
        self.pipeline.queue.clear()
        with self.interrupt_lock:
            self.pause_flag = False

    def check_task_completion(self):
        """
        Checks whether the tasks currently running are complete.
        """
        incomplete_tasks = []
        for task in self.tasks:
            if task.is_complete:
                if task.error:
                    if not self.error:
                        self.pause_all()
                        self.write_log(f"The robot has hit an error. Please use the GUI to correct and press resume.",
                                       level=logging.ERROR)
                        if self.gui_main:
                            self.gui_main.pause_butt.configure(text="Resume", bg="lawn green",
                                                               command=self.gui_main.resume)
                        with self.interrupt_lock:
                            self.pause_flag = True
                            self.error = True
                        self.error_start = time.time()
                        self.listener.update_status(self.ready, self.error)
                    incomplete_tasks.append(task)
            else:
                incomplete_tasks.append(task)
        self.tasks = incomplete_tasks

    def pause_all(self):
        """
        Pauses all currently running tasks and queue execution.
        """
        self.paused = True
        self.pause_flag = True
        for task in self.tasks:
            if not task.module_ready:
                task.pause()
        if self.stop_flag:
            self.stop_all()

    def stop_all(self):
        """
        Removes all queued actions, should be called after pause if stopping.
        """
        self.tasks = []
        with self.q.mutex:
            self.q.queue.clear()
        self.paused = False
        self.pause_flag = False
        self.stop_flag = False
        self.execute = False
        self.error = False
        self.error_flag = False
        self.reaction_name = ""

    def resume(self):
        """
        Resumes all tasks in the task list
        """
        new_q = Queue()
        for cnt, task in enumerate(self.tasks):
            # module"s resume method determines appropriate resume command based on module type.
            resume_flag = task.resume()
            if resume_flag is not False:
                for cmd in task.command_dicts:
                    new_q.put(cmd)
            self.tasks.pop(cnt)
        while not self.q.empty():
            command_dict = self.q.get(block=False)
            new_q.put(command_dict)
        self.q = new_q
        self.error_flag = False
        self.error = False
        self.pause_flag = False
        self.paused = False

    def command_module(self, command_dict):
        """
        Interprets the command dict to command the necessary module

        Args:
            command_dict (dict): dictionary containing all necessary information for the action
        Returns:
            Function call to necessary module, or False if no suitable modules can be found.
        """
        try:
            mod_type, name = command_dict["mod_type"], command_dict["module_name"]
            command, parameters = command_dict["command"], command_dict["parameters"]
        except KeyError:
            self.write_log("Missing parameters: module type, name, command, parameters", level=logging.WARNING)
            return False
        if mod_type == "selector_valve":
            return self.command_valve(name, command, parameters, command_dict)
        elif mod_type == "syringe_pump":
            return self.command_syringe(name, command, parameters, command_dict)
        elif mod_type == "reactor":
            return self.command_reactor(name, command, parameters, command_dict)
        elif mod_type == "camera":
            return self.command_camera(name, command, parameters, command_dict)
        elif mod_type == "wait":
            return self.command_wait(name, command, parameters, command_dict)
        else:
            self.write_log(f"{mod_type} is not recognised", level=logging.WARNING)
            return False

    def command_syringe(self, name, command, parameters, command_dict):
        """
        Interprets the command dictionary for syringe actions

        Args:
            name (str): The syringe name
            command (str): The action to be performed
            parameters (dict): Contains the parameters for the action
            command_dict (dict): the full command dictionary for the action
        """
        new_task = Task(command_dict, self.syringes[name])
        self.tasks.append(new_task)
        if command == "move":
            target = parameters["target"]
            volume = parameters["volume"]
            flow_rate = parameters["flow_rate"]
            direction = parameters["direction"]
            air = parameters.get("air")
            track_volume = parameters.get("track_volume")
            if not track_volume and track_volume is not None:
                target = None
            elif target is None:
                adj = [key for key in self.graph.adj[name].keys()]
                try:
                    valve = adj[0]
                    valve = self.graph.nodes[valve]["object"]
                    parameters["target"] = valve.ports[valve.current_port]
                    target = parameters["target"]
                except KeyError:
                    target = None
            elif isinstance(target, str):
                parameters["target"] = self.find_target(target)
                target = parameters["target"]
            cmd_thread = Thread(target=self.syringes[name].move_syringe, name=name + "move",
                                args=(target, volume, flow_rate, direction, air, new_task))
        elif command == "home":
            cmd_thread = Thread(target=self.syringes[name].home, name=name + "home")
        elif command == "jog":
            cmd_thread = Thread(target=self.syringes[name].jog, name=name + "jog",
                                args=(parameters["steps"], parameters["direction"], new_task))
        elif command == "setpos":
            position = parameters["pos"]
            cmd_thread = Thread(target=self.syringes[name].set_pos, name=name + "setpos", args=(position,))
        else:
            self.write_log(f"Command {command} is not recognised", level=logging.WARNING)
            return False
        new_task.add_worker(cmd_thread)
        cmd_thread.start()
        if parameters["wait"]:
            self.wait_until_ready()
        return True

    def command_valve(self, name, command, parameters, command_dict):
        """
        Interprets the command dictionary for the valve

        Args:
            name (str): the name of the valve
            command (str/int): the command type
            parameters (dict): parameters for the action
            command_dict (dict): the full dictionary for the action
        Returns:
            bool - True if command successfully sent, otherwise False
        """
        new_task = Task(command_dict, self.valves[name])
        self.tasks.append(new_task)
        if type(command) is int and 0 <= command < 11:
            port = command
            cmd_thread = Thread(target=self.valves[name].move_to_pos, name=name + "movepos", args=(port,))
        elif command == "target":
            target = parameters["target"]
            cmd_thread = Thread(target=self.valves[name].move_to_target, name=name + "targetmove",
                                args=(target, new_task))
        elif command == "home":
            cmd_thread = Thread(target=self.valves[name].home_valve, name=name + "home")
        elif command == "zero":
            cmd_thread = Thread(target=self.valves[name].zero, name=name + "zero", args=(new_task,))
        elif command == "jog":
            steps = parameters["steps"]
            invert_direction = parameters["invert_direction"]
            cmd_thread = Thread(target=self.valves[name].jog, name=name + "jog", args=(steps, invert_direction))
        elif command == "he_sens":
            cmd_thread = Thread(target=self.valves[name].he_read, name=name + "sens")
        else:
            self.write_log(f"{command} is not a valid command", level=logging.WARNING)
            return False
        new_task.add_worker(cmd_thread)
        cmd_thread.start()
        if parameters["wait"]:
            self.wait_until_ready()
        return True

    def find_target(self, target):
        """
        Finds a module on the robot

        Args:
            target (str): the name of the target, or the name of the module type, e.g., "reactor"
        Returns:
            module object (Module): The target module if found, otherwise None
        """
        for key in self.modules.keys():
            target = self.modules[key].get(target)
            if target is not None:
                break
        return target

    def find_reagent(self, reagent_name):
        """
        Finds a reagent in the attached flasks

        Args:
            reagent_name (str): the name of the reagent to search for
        Returns:
            reagent name or empty string if nothing found
        """
        reagent_name = reagent_name.lower()
        for flask in self.flasks:
            if reagent_name == self.flasks[flask].contents[0]:
                return self.flasks[flask].name
        return ""

    def command_reactor(self, name, command, parameters, command_dict):
        """
        Interprets the command dictionary for a reactor action

        Args:
            name (str): the name of the reactor
            command (str): the name of the action
            parameters (dict): dictionary containing parameters for the action
            command_dict (dict): full dictionary for the action
        """
        new_task = Task(command_dict, self.reactors[name], single_action=False)
        self.tasks.append(new_task)
        if command == "start_stir":
            speed = parameters["speed"]
            stir_secs = parameters["stir_secs"]
            self.reactors[name].start_stir(speed, stir_secs)
            self.reactors[name].stir_task = new_task
        elif command == "stop_stir":
            self.reactors[name].stop_stir()
            new_task.complete = True
        elif command == "start_heat":
            temp = parameters["temp"]
            heat_secs = parameters["heat_secs"]
            target = parameters["target"]
            self.reactors[name].start_heat(temp, heat_secs, target, new_task)
            self.reactors[name].heat_task = new_task
        elif command == "stop_heat":
            self.reactors[name].stop_heat()
            new_task.complete = True
        else:
            self.write_log(f"{command} is not a valid command", level=logging.WARNING)
            return False
        new_task.add_worker(self.reactors[name].thread)
        if parameters.get("wait"):
            self.wait_until_ready()
        return True

    def command_camera(self, name, command, parameters, command_dict):
        """
        Interprets the command dictionary for a camera action

        Args:
            name (str): the name of the reactor
            command (str): the name of the action
            parameters (dict): dictionary containing parameters for the action
            command_dict (dict): full dictionary for the action
        """
        new_task = Task(command_dict, self.cameras[name])
        self.tasks.append(new_task)
        if command == "send_img":
            img_num = parameters["img_num"]
            img_processing = parameters["img_processing"]
            cmd_thread = Thread(target=self.send_image, name=name+"send_image",
                                args=(img_num, img_processing, new_task))
            self.write_log(f"Taking image {img_num}", level=logging.INFO)
        else:
            self.write_log(f"Unknown command {command}", level=logging.ERROR)
            return False
        new_task.add_worker(cmd_thread)
        cmd_thread.start()
        if parameters["wait"]:
            self.wait_until_ready()
        return True        

    def command_wait(self, name, command, parameters, command_dict):
        """
        Interprets the command dictionary for a wait action

        Args:
            name (str): the name of the manager
            command (str): the name of the action
            parameters (dict): dictionary containing parameters for the action
            command_dict (dict): full dictionary for the action
        """
        new_task = Task(command_dict, name)
        self.tasks.append(new_task)
        wait_reason = parameters["wait_reason"]
        if command == "wait_user":
            self.user_wait_flag = False
            cmd_thread = Thread(target=self.wait_user, name=name+"wait_user", args=())
            self.write_log(f"Waiting for user resume, reason: {wait_reason}", level=logging.INFO)
        elif command == "wait":
            wait_time = parameters["time"]
            cmd_thread = Thread(target=self.wait_until, name=name+"wait_until", args=(wait_time,))
            self.write_log(f"Waiting for {wait_time} s, reason: {wait_reason}", level=logging.INFO)
        else:
            return False
        new_task.add_worker(cmd_thread)
        cmd_thread.start()
        if parameters["wait"]:
            self.wait_until_ready()
        return True

    def command_storage(self, name, command, parameters, command_dict):
        """
        Interprets the command dictionary for the storage device

        Args:
            name (str): the name of the storage device
            command (str): the command type
            parameters (dict): the parameters for the action
            command_dict (dict): the full dictionary for the action
        Returns:
            bool - True if command successfully sent
        """
        new_task = Task(command_dict, self.storage[name])
        self.tasks.append(new_task)
        if command == "turn":
            cmd_thread = Thread(target=self.storage[name].turn_wheel, name=name + "turnwheel",
                                args=(parameters["num_turns"], parameters["direction"]))
        elif command == "move_to":
            cmd_thread = Thread(target=self.storage[name].move_to_position, name=name + "moveto",
                                args=(parameters["position"],))
        elif command == "store":
            cmd_thread = Thread(target=self.storage[name].add_sample, name=name + "store", args=(new_task,))
        elif command == "remove":
            cmd_thread = Thread(target=self.storage[name].remove_sample, name=name + "remove")
        else:
            self.write_log(f"{command} is not a valid command", level=logging.WARNING)
            return False
        new_task.add_worker(cmd_thread)
        cmd_thread.start()
        if parameters["wait"]:
            self.wait_until_ready()
        return True

    def wait_until_ready(self):
        """
        Waits for the last sent action to complete
        """
        with self.interrupt_lock:
            self.waiting = True
    
    def wait_user(self):
        """
        Waits for user input, either via the console or GUI
        """
        if self.gui_main is None:
            input("Ready to resume? Press any key")
        else:
            self.gui_main.wait_user()
            while not self.user_wait_flag:
                time.sleep(1)

    @staticmethod
    def wait_until(wait_time):
        """
        Waits for a specified time before getting new actions from the queue
        """
        start_time = time.time()
        while time.time() - start_time < wait_time:
            time.sleep(1)
        
    def move_fluid(self, source, target, volume, flow_rate, init_move=False, adjust_dead_vol=True, transfer=False):
        """
        Adds the necessary command dicts to the pipeline to enact a fluid movement from source to target

        Args:
            source (str): the name of the source module
            target (str): the name of the target module
            volume (float): the volume of fluid in uL to be moved
            flow_rate (int): uL per second to move
            init_move (bool): whether this is an initialisation move (clearing lines from prev run) not
            adjust_dead_vol (bool): Whether to account for dead volume in tubing
            transfer (bool): Whether the fluid involves transfer from a source other than a reagent bottle
        Returns:
            True if successfully queued or False otherwise
        """

        # Returns a simple path from source to target. No nodes are repeated.
        path = self.find_path(source, target)
        if len(path) < 1:
            return False
        pipelined_steps = []
        volume = (volume * 1000) + 50  # testing shows ~50 ul remains in the syringe after transfers
        prev_max_vol = 999999.00
        max_vol = self.valves[path[1]].syringe.max_volume
        min_vol = 0
        tdv = 0
        spdv = 0
        if flow_rate == 0:
            flow_rate = self.default_fr
        # Grab intervening valves between source and target
        valves = path[1:-1]
        # Aspirate enough air to flush all the fluid at the end of the movement
        if adjust_dead_vol and not init_move:
            steps, spdv = self.flush_sp_dead_volume(valves[-1], target, True)
            pipelined_steps += steps
        # If we are transferring fluid (i.e not from reagent lines), we need to account for dead volume between
        # the source and the valve as well.
        if transfer:
            steps, tdv = self.flush_transfer_dead_volume(valves[0], source, True)
            pipelined_steps += steps
        target = self.find_target(target)
        source = self.find_target(source)
        if target.mod_type == "storage":
            pipelined_steps += self.generate_cmd_dict("storage", target.name, "store", {})
        # Find lowest maximum volume amongst syringes
        dead_volume = tdv + spdv
        for valve in valves:
            cur_max_vol = self.valves[valve].syringe.max_volume
            if cur_max_vol < prev_max_vol:
                max_vol = cur_max_vol
                min_vol = self.valves[valve].syringe.min_volume
        max_volume = max_vol - min_vol - dead_volume
        nr_full_moves = int(volume / max_volume)
        remaining_volume = volume % max_volume
        if nr_full_moves >= 1:
            full_move = self.generate_moves(source, target, valves, max_volume, flow_rate,
                                            adjust_dead_vol, init_move)
            for i in range(0, nr_full_moves):
                pipelined_steps += full_move
        if remaining_volume > 0.0:
            partial_move = self.generate_moves(source, target, valves, remaining_volume, flow_rate,
                                               adjust_dead_vol, init_move)
            pipelined_steps += partial_move
        # Flush the tubing between last valve and destination using air from earlier.
        if adjust_dead_vol and not init_move:
            steps, spdv = self.flush_sp_dead_volume(valves[-1], target, intake=False)
            pipelined_steps += steps
        # If conducting a transfer, flush remaining air.
        if transfer and source not in self.flasks:
            steps, tdv = self.flush_transfer_dead_volume(valves[0], source, intake=False)
            pipelined_steps += steps
        self.add_to_queue(pipelined_steps, self.pipeline)
        return True

    def find_path(self, source, target):
        """
        Finds a path using networkx graph from source to target

        Args:
            source (str): the name of the source module
            target (str): the name of the target module
        """
        source_found = False
        target_found = False
        if source in self.valid_nodes:
            source_found = True
        if target in self.valid_nodes:
            target_found = True
        if source_found and target_found:
            paths = nx.algorithms.all_simple_paths(self.graph, source, target)
            path_list = [p for p in paths]
            if path_list:
                return path_list[0]
        if not source_found:
            self.write_log(f"{source} not present", level=logging.WARNING)
        if not target_found:
            self.write_log(f"{target} not present", level=logging.ERROR)
        return []

    def flush_sp_dead_volume(self, valve, target, intake):
        """Remove the dead volume in the tubing using air. Called twice to add necessary steps, first call intake=True
        lets syringe take in necessary volume of air to empty tubing, second call intake=False dispense the air into
        the target, clearing the tubing.

        Args:
            valve (SelectorValve): The last valve in the chain
            target (str): The name of the target
            intake (bool): Whether we are aspirating the dead volume or dispensing it
        Return:
            pipelined_steps (list): List containing the necessary steps as command dictionaries
            dead_volume (float): The amount of dead volume (uL) between the valve and the target
        """
        pipelined_steps = []
        # The tubes along the path will hold dead volume, assuming all input lines have been primed before operation.
        valve = self.valves[valve]
        tubing_length = self.graph.adj[valve.name][target][0]["tubing_length"]
        dead_volume = self.calc_tubing_volume(tubing_length)*1.15  # push out a bit extra to ensure tube empty
        if intake:
            if valve.find_open_port() is None:
                return
            # Command to index valve to required position for air
            pipelined_steps += self.generate_cmd_dict("selector_valve", valve.name, "target",
                                                      {"target": "empty", "wait": True})
            # Command to aspirate air to fill dead volume
            pipelined_steps += self.generate_cmd_dict("syringe_pump", valve.syringe.name, "move",
                                                      {"volume": dead_volume, "flow_rate": self.default_flush_fr,
                                                       "target": None, "direction": "A", "air": True, "wait": True})
        else:
            # dispense dead volume of air into target, emptying the dead volume in the tube
            pipelined_steps += self.generate_cmd_dict("syringe_pump", valve.syringe.name, "move",
                                                      {"volume": dead_volume, "flow_rate": self.default_flush_fr,
                                                       "target": None, "direction": "D", "air": True, "wait": True})
        return pipelined_steps, dead_volume

    def flush_transfer_dead_volume(self, valve, source, intake):
        pipelined_steps = []
        valve = self.valves[valve]
        tubing_length = self.graph.adj[valve.name][source][0]["tubing_length"]
        dead_volume = self.calc_tubing_volume(tubing_length)

        if intake:
            # Command to index valve to required position to remove dead volume in tube
            pipelined_steps += self.generate_cmd_dict("selector_valve", valve.name, "target",
                                                      {"target": source, "wait": True})
            # Command to aspirate syringe to remove dead volume - doesn't update volumes
            pipelined_steps += self.generate_cmd_dict("syringe_pump", valve.syringe.name, "move",
                                                      {"volume": dead_volume, "flow_rate": self.default_flush_fr,
                                                       "target": None, "direction": "A", "air": True, "wait": True})
        else:
            # Command to index valve to required position for outlet
            pipelined_steps += self.generate_cmd_dict("selector_valve", valve.name, "target",
                                                      {"target": source, "wait": True})
            # Command to dispense air to blow out dead volume
            pipelined_steps += self.generate_cmd_dict("syringe_pump", valve.syringe.name, "move",
                                                      {"volume": dead_volume, "flow_rate": self.default_flush_fr,
                                                       "target": source, "direction": "D", "air": True, "wait": True})
        return pipelined_steps, dead_volume

    @staticmethod
    def calc_tubing_volume(tubing_length):
        mm3 = math.pow((1.5875 / 2), 2) * math.pi * tubing_length
        return mm3

    def generate_moves(self, source, target, valves, volume, flow_rate, adjust_dead_vol, init_move=False):
        """
        Generates the moves required to transfer liquid from source to target

        Args:
            source (str): name of the source
            target (str): name of the target
            valves (list): Intervening valves between source and target
            volume (float): Volume to be moved
            flow_rate (int): Flow rate in ul/min
            adjust_dead_vol (bool): whether to correct for dead volumes in tubing
            init_move (bool): whether this is an initialisation move or not
        Returns:
            moves (list): the moves to queue
        """
        moves = []
        valve = self.valves[valves[0]]
        source = self.graph.nodes[source]["object"]
        if target is not None:
            target = self.graph.nodes[target]["object"]
        # Move liquid into first syringe pump
        if not init_move:
            moves += self.generate_sp_move(source, valve, valve.syringe, volume, flow_rate)
        # transfer liquid along backbone
        if len(valves) > 1:
            for i in range(len(valves) - 1):
                valve = self.valves[valves[i]]
                next_valve = self.valves[valves[i + 1]]
                moves += self.generate_sp_transfer(valve, next_valve, volume, flow_rate, adjust_dead_vol)
        # Move liquid from last syringe pump into target
        valve = self.valves[valves[-1]]
        moves += self.generate_sp_move(valve.syringe, valve, target, volume, flow_rate)
        return moves

    @staticmethod
    def generate_sp_move(source, valve, target, volume, flow_rate):
        """
        Generates the commands to dispense or aspirate a syringe
        Args:
            source (Module): Module object for the source
            valve (Module): SelectorValve
            target (Module): Module object for the target
            volume (float): volume to move in uL
            flow_rate (int): flow rate in uL/min
        Returns:
            commands (list): List containing the command dictionaries for the move
        """
        commands = []
        # Dispense from SP
        if source.mod_type == "SP":
            direction = "D"
            name = source.name
            if not target:
                target_name = "empty"
            else:
                target_name = target.name
        # Aspirate into SP
        else:
            direction = "A"
            name = target.name
            if not source:
                target_name = "empty"
            else:
                target_name = source.name

        # Command to index valve to required position
        commands += Manager.generate_cmd_dict("selector_valve", valve.name, "target",
                                              {"target": target_name, "wait": True})
        # Command to dispense/withdraw syringe
        commands += Manager.generate_cmd_dict("syringe_pump", name, "move",
                                              {"volume": volume, "flow_rate": flow_rate, "target": target_name,
                                               "direction": direction, "wait": True})
        return commands

    def generate_sp_transfer(self, source_valve, target_valve, volume, flow_rate, account_for_dead_volume):
        """
        Generates the commands necessary to transfer liquid between two adjacent valves

        Args:
        source_valve (SelectorValve): source valve object
        target_valve (SelectorValve): target valve object
        volume (float): volume to be transferred in uL
        flow_rate (int): flow rate in ul/min

        Returns:
         list of command dicts
        """
        commands = []
        source_port = None
        target_port = None
        for adj_valve in source_valve.adj_valves:
            if target_valve.name in adj_valve[0]:
                source_port = adj_valve[1]
        for adj_valve in target_valve.adj_valves:
            if source_valve.name in adj_valve[0]:
                target_port = adj_valve[1]
        if source_port is None or target_port is None:
            return False
        if account_for_dead_volume:
            # determine dead volume between valves
            tubing_length = self.graph.adj[source_valve][target_valve][0]["tubing_length"]
            dead_volume = self.calc_tubing_volume(tubing_length)*1.15
            # take up air to flush dead volume
            commands += self.generate_cmd_dict("selector_valve", source_valve.name, "target",
                                               {"target": "empty", "wait": True})
            commands += self.generate_cmd_dict("syringe_pump", source_valve.syringe.name, "move",
                                               {"volume": dead_volume, "flow_rate": self.default_flush_fr,
                                                "direction": "A", "air": True, "wait": True})
            volume = volume + dead_volume
        # add commands to index valves to required ports for transfer
        commands += self.generate_cmd_dict("selector_valve", source_valve.name, source_port,
                                           {"wait": True})
        commands += self.generate_cmd_dict("selector_valve", target_valve.name, target_port,
                                           {"wait": True})
        # Command to dispense source syringe into target syringe. Does not signal Manager to wait for completion.
        commands += self.generate_cmd_dict("syringe_pump", source_valve.syringe.name, "move",
                                           {"volume": volume, "flow_rate": flow_rate,
                                            "target": target_valve.syringe.name,
                                            "direction": "D", "wait": False})
        # Command to aspirate target syringe to accept contents of source syringe. Signals manager to
        # wait for completion.
        commands += self.generate_cmd_dict("syringe_pump", target_valve.syringe.name, "move",
                                           {"volume": volume, "flow_rate": flow_rate,
                                            "target": source_valve.syringe.name,
                                            "direction": "A", "wait": True})
        return commands

    def correct_position_error(self, syringe):
        valve = syringe.valve
        current_valve_port = valve.current_port
        self.write_log("Repositioning valve")
        valve.home_valve()
        valve.move_to_pos(current_valve_port)

    def start_stirring(self, reactor_name, command, speed, stir_secs, wait):
        params = {"speed": speed, "stir_secs": stir_secs, "wait": wait}
        command_dict = Manager.generate_cmd_dict("reactor", reactor_name, command, params)
        self.add_to_queue(command_dict)

    def start_heating(self, reactor_name, command, temp, heat_secs, wait,  target=False):
        """Adds a command to start heating the reactor to the manager queue

        Args:
            reactor_name (str): Name of the reactor to start heating
            command (str): command name (start_heat)
            temp (float): Temperature to heat the reactor to
            heat_secs (int): Time in seconds to heat reactor for.
             If 0, then reactor will just maintain the set temperature until the Manager"s queue is exhausted.
            wait ([type]): [description]
            target (bool, optional): [description]. Defaults to False.
        """
        params = {"temp": temp, "heat_secs": heat_secs, "wait": wait, "target": target}
        command_dict = Manager.generate_cmd_dict("reactor", reactor_name, command, params)
        self.add_to_queue(command_dict)

    def stop_reactor(self, reactor_name, command):
        if command == "stop_stir":
            command_dict = Manager.generate_cmd_dict("reactor", reactor_name, command, {})
            self.add_to_queue(command_dict)
        elif command == "stop_heat":
            command_dict = Manager.generate_cmd_dict("reactor", reactor_name, command, {})
            self.add_to_queue(command_dict)
    
    def send_image(self, img_num, img_processing, task):
        cam = self.cameras["camera1"]
        image_metadata = {"robot_id": self.id, "robot_key": self.key, "reaction_id": self.reaction_id,
                          "img_number": img_num,
                          "reaction_name": self.reaction_name, "img_processing": img_processing, "img_roi": cam.roi}
        cam.send_image(self.listener, image_metadata, task)
    
    def wait(self, wait_time, actions):
        pic_info = actions.get("picture")
        wait_info = actions.get("wait_user")
        wait_reason = actions.get("wait_reason")
        img_processing = actions.get("img_processing")
        if wait_reason is None:
            wait_reason = ""
        if wait_info is not None:
            manager_wait = True
            if wait_reason == "cleaning":
                manager_wait = False
            command_dict = Manager.generate_cmd_dict(mod_type="wait", mod_name="wait",
                                                     command="wait_user",
                                                     parameters={"wait": manager_wait, "wait_reason": wait_reason})
            self.add_to_queue(command_dict)
        else:
            command_dict = Manager.generate_cmd_dict(mod_type="wait", mod_name="wait",
                                                     command="wait",
                                                     parameters={"time": wait_time, "wait": True,
                                                                 "wait_reason": wait_reason})
            self.add_to_queue(command_dict)
        if pic_info is not None:
            command_dict = Manager.generate_cmd_dict(mod_type="camera", mod_name="camera1",
                                                     command="send_img",
                                                     parameters={"img_num": pic_info,
                                                                 "img_processing": img_processing, "wait": True})
            self.add_to_queue(command_dict)

    @classmethod
    def generate_cmd_dict(cls, mod_type, mod_name, command, parameters):
        return [{"mod_type": mod_type, "module_name": mod_name, "command": command, "parameters": parameters}]

    def ensure_reactors_disabled(self):
        for r in self.reactors:
            if self.reactors[r].heating and self.reactors[r].heat_start_time - time.time() > 300:
                r.stop_heat()
            if self.reactors[r].stirring and self.reactors[r].stir_start_time - time.time() > 300:
                self.reactors[r].stop_stir()

    def home_all_valves(self):
        home_cmds = []
        for valve in self.valves:
            home_cmds.append({"mod_type": "selector_valve", "module_name": valve, "command": "home",
                              "parameters": {"wait": True}})
        self.add_to_queue(home_cmds, self.q)

    def exit_program(self):
        self.stop_flag = True
        self.pause_all()
        for cam in self.cameras:
            self.cameras[cam].exit_flag = True
        for valve in self.valves:
            self.prev_run_config["valve_pos"][valve] = self.valves[valve].current_port
        self.write_running_config("configs\\running_config.json")
        if self.gui_main:
            while not self.gui_main.safe_quit_flag:
                time.sleep(0.2)
            self.gui_main.primary.destroy()
            self.gui_main.primary.quit()
        for handler in self.cmd_mng.commandhandlers:
            handler.stop()


class Task:
    """
    Class to represent queued tasks. Primarily used to pause, resume, or stop all queued tasks.
    """

    def __init__(self, command_dict, module, single_action=True):
        self.command_dict = command_dict
        self.command_dicts = [self.command_dict]
        self.module = module
        self.worker = None
        self.single_action = single_action
        self.complete = False
        self.paused = False
        self.error = False
        
    def add_worker(self, thread):
        self.worker = thread

    def pause(self):
        self.command_dict = self.module.stop()
        self.paused = True

    def resume(self):
        resume_flag = self.module.resume(self.command_dicts)
        self.error = False
        return resume_flag

    @property
    def is_complete(self):
        if self.single_action:
            if self.worker.is_alive() or self.paused:
                self.complete = False
            else:
                self.complete = True
        return self.complete

    @property
    def module_ready(self):
        return self.module.ready