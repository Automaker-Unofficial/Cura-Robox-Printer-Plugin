import enum


class Model(enum.Enum):
    dual = "cel_robox_dual"
    quick_fill = "cel_robox_quickfill"


class Tool(enum.Enum):
    T0 = "T0"
    T1 = "T1"


extrusion_letter = {
    Model.quick_fill: {
        Tool.T0: "E",
        Tool.T1: "E"
    },
    Model.dual: {
        Tool.T0: "D",
        Tool.T1: "E"
    },
}

nozzle_diameter = {
    Model.quick_fill: {
        Tool.T0: 0.8,
        Tool.T1: 0.3
    },
    Model.dual: {
        Tool.T0: 0.4,
        Tool.T1: 0.4
    },
}

valve_volume = {
    Model.quick_fill: {
        Tool.T0: 0.6,
        Tool.T1: 0.3
    },
    Model.dual: {
        Tool.T0: 0.3,
        Tool.T1: 0.3
    },
}


class Printhead:
    def __init__(self, model: Model):
        super().__init__()
        self.model = model
        self.extrusion_letters = extrusion_letter[model]
        self.nozzle_diameters = nozzle_diameter[model]
        self.valve_volumes = valve_volume[model]

    def get_extrusion_letter(self, tool: str) -> str:

        return self.extrusion_letters[Tool(tool)]

    def get_nozzle_diameter(self, tool: str) -> float:
        return self.nozzle_diameters[Tool(tool)]

    def get_valve_volume(self, tool: str) -> float:
        return self.valve_volumes[Tool(tool)]

    def get_valve_open_fill_line(self, tool: str) -> str:
        return f"G1 B1 F150 E{round(self.get_nozzle_diameter(Tool(tool)) * 0.75, 3)}; open valve and fill the nozzle {tool} with filament"

    # converts valve volume into valve opening percents
    def get_valve_opening(self, tool: str, volume_to_extrude: float):
        value = round(1 - (volume_to_extrude / self.get_valve_volume(Tool(tool))), 2)
        if value == 0:
            return 0
        return value
