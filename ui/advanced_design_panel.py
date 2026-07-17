from PySide6.QtWidgets import QLabel,QTableWidget,QTableWidgetItem,QTabWidget,QVBoxLayout,QWidget

class AdvancedDesignPanel(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); lay=QVBoxLayout(self); self.note=QLabel("Run analysis, then Advanced Concrete Checks."); self.note.setWordWrap(True); lay.addWidget(self.note)
        self.tabs=QTabWidget(); self.beams=QTableWidget(0,10); self.columns=QTableWidget(0,8); self.slabs=QTableWidget(0,11)
        self.beams.setHorizontalHeaderLabels(["Beam","Vu","Stirrups","Tu","Torsion","Ld","Defl","Limit","Service","Status"])
        self.columns.setHorizontalHeaderLabels(["Column","Pu","Mu","P-M","As req","Bars","Status","Label"])
        self.slabs.setHorizontalHeaderLabels(["Slab","Punch","Punch Status","ST Defl","LT Defl","Limit","Service","Top X","Top Y","Bot X","Bot Y"])
        self.tabs.addTab(self.beams,"Beam Checks"); self.tabs.addTab(self.columns,"Column P-M"); self.tabs.addTab(self.slabs,"Slab / Punching"); lay.addWidget(self.tabs)
    def _fill(self,t,rows):
        t.setRowCount(len(rows))
        for r,row in enumerate(rows):
            for c,v in enumerate(row): t.setItem(r,c,QTableWidgetItem(str(v)))
        t.resizeColumnsToContents()
    def clear_design(self):
        [t.setRowCount(0) for t in (self.beams,self.columns,self.slabs)]; self.note.setText("Run analysis, then Advanced Concrete Checks.")
    def set_design(self,res):
        self._fill(self.beams,[[f"F{x.frame_id}",f"{x.shear_kn:.3f}",f"Ø10@{x.stirrup_spacing_mm:.0f}",f"{x.torsion_knm:.3f}",x.torsion_status,f"{x.development_length_mm:.0f}",f"{x.deflection_mm:.3f}",f"{x.limit_mm:.3f}",x.status,x.status] for x in res.beams.values()])
        self._fill(self.columns,[[f"F{x.frame_id}",f"{x.axial_kn:.3f}",f"{x.moment_knm:.3f}",f"{x.ratio:.3f}",f"{x.required_as_mm2:.1f}",x.bars,x.status,f"{x.bars}Ø20"] for x in res.columns.values()])
        self._fill(self.slabs,[[f"A{x.area_id}",f"{x.punching_ratio:.3f}",x.punching_status,f"{x.short_mm:.3f}",f"{x.long_mm:.3f}",f"{x.limit_mm:.3f}",x.service_status,x.top_x,x.top_y,x.bottom_x,x.bottom_y] for x in res.slabs.values()])
        self.note.setText("<b>Expanded preliminary checks.</b> "+" ".join(res.warnings))
