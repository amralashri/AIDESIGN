from __future__ import annotations
from dataclasses import dataclass

MAPS = {
    "length": {"m":1.0,"cm":100.0,"mm":1000.0,"ft":3.280839895,"in":39.37007874},
    "area": {"m²":1.0,"cm²":1e4,"mm²":1e6,"ft²":10.76391042,"in²":1550.0031},
    "force": {"kN":1.0,"N":1000.0,"MN":0.001,"tf":0.1019716213,"kip":0.2248089439},
    "moment": {"kN·m":1.0,"N·m":1000.0,"kN·mm":1000.0,"tf·m":0.1019716213,"kip·ft":0.7375621493},
    "stress": {"kPa":1.0,"MPa":0.001,"Pa":1000.0,"N/mm²":0.001,"psi":0.1450377377},
    "displacement": {"m":1.0,"cm":100.0,"mm":1000.0,"in":39.37007874},
}

@dataclass(slots=True)
class UnitSelection:
    length:str="m"
    area:str="m²"
    force:str="kN"
    moment:str="kN·m"
    stress:str="MPa"
    displacement:str="mm"

class _Signal:
    def __init__(self):
        self._callbacks=[]
    def connect(self,callback):
        if callback not in self._callbacks:self._callbacks.append(callback)
    def disconnect(self,callback):
        if callback in self._callbacks:self._callbacks.remove(callback)
    def emit(self):
        for callback in list(self._callbacks):callback()

class UnitSystem:
    def __init__(self,parent=None):
        self.selection=UnitSelection()
        self.changed=_Signal()
    def set_unit(self,quantity,unit):
        if unit not in MAPS[quantity]:
            raise ValueError(f"Unsupported {quantity} unit: {unit}")
        setattr(self.selection,quantity,unit)
        self.changed.emit()
    def unit(self,quantity):
        return getattr(self.selection,quantity)
    def convert(self,value,quantity):
        return float(value)*MAPS[quantity][self.unit(quantity)]
    def format(self,value,quantity,decimals=3):
        return f"{self.convert(value,quantity):.{decimals}f} {self.unit(quantity)}"
    def force_component(self,value):
        return self.format(value,"force")
    def moment_component(self,value):
        return self.format(value,"moment")
    def displacement_component(self,value):
        return self.format(value,"displacement",5)
    def shell_result(self,key,value):
        if key in ("Mx","My","Mxy","Mmax","Mmin"):
            return f"{self.convert(value,'force'):.3f} {self.unit('force')}·m/m"
        if key in ("Nx","Ny","Nxy","Qx","Qy"):
            return f"{self.convert(value,'force'):.3f} {self.unit('force')}/m"
        if key=="w":
            return self.displacement_component(value)
        return f"{value:.4g}"
