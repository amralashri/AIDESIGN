from PySide6.QtWidgets import QComboBox,QHBoxLayout,QLabel,QWidget
from core.units import MAPS,UnitSystem

class UnitStatusWidget(QWidget):
    def __init__(self,unit_system:UnitSystem,parent=None):
        super().__init__(parent)
        layout=QHBoxLayout(self)
        layout.setContentsMargins(6,0,0,0)
        layout.setSpacing(3)
        layout.addWidget(QLabel("Units:"))
        for quantity,label in [
            ("length","L"),("area","A"),("force","F"),
            ("moment","M"),("stress","σ"),("displacement","Δ")
        ]:
            layout.addWidget(QLabel(label))
            combo=QComboBox()
            combo.addItems(list(MAPS[quantity]))
            combo.setCurrentText(unit_system.unit(quantity))
            combo.currentTextChanged.connect(
                lambda unit,q=quantity:unit_system.set_unit(q,unit)
            )
            combo.setMinimumWidth(66 if quantity!="moment" else 82)
            layout.addWidget(combo)
        self.setStyleSheet("""
        QComboBox{min-height:20px;padding:1px 5px;border:1px solid #b7c6d2;
        border-radius:4px;background:white} QLabel{font-size:8.5pt;color:#37474f}
        """)
