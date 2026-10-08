"""Measured physical-to-virtual correspondences; never writes to a motor."""
import json
import math
from dataclasses import asdict
from .robot import JOINT_NAMES, joint_limits
from .joint_binding import JointBinding, RobotBinding


def build_binding_dialog(panel):
    from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QGridLayout,QDoubleSpinBox,QPushButton,QFileDialog
    dialog=QDialog(panel);dialog.setWindowTitle('Measure virtual joint binding');dialog.resize(850,420)
    layout=QVBoxLayout(dialog)
    back=QPushButton('Back to hardware controls');back.clicked.connect(dialog.reject);layout.addWidget(back)
    note=QLabel('With motors stopped, move each physical joint to two known poses. Enter the corresponding virtual angle and capture A, then B. Capture each joint separately. Calibration midpoint is not assumed to be the CAD zero.')
    note.setWordWrap(True);layout.addWidget(note)
    grid=QGridLayout();layout.addLayout(grid);captures={};angles={};labels={}
    for column,title in enumerate(('Joint','Virtual angle','Pose A','Pose B')):grid.addWidget(QLabel(title),0,column)
    status=QLabel();status.setWordWrap(True)
    def capture(name,index):
        snapshot=panel.session.snapshot();sample=snapshot['sample']
        if snapshot['state']!='read-only' or snapshot['stale'] or not sample or name not in sample['observations']:
            status.setText('Connect read-only with matching calibration and fresh readings before capturing.');return
        if any(m['torque'] for m in sample['motors'].values()):
            status.setText('Support the arm and Stop motors before moving it by hand.');return
        observed=sample['observations'][name];radians=math.radians(angles[name].value())
        captures[name,index]=(observed,radians)
        labels[name,index].setText(f'{observed:.2f} → {math.degrees(radians):.1f}°')
    for row,name in enumerate(JOINT_NAMES,1):
        grid.addWidget(QLabel(name.replace('_',' ').title()),row,0)
        spin=QDoubleSpinBox();spin.setDecimals(2);spin.setSuffix('°');spin.setRange(*(math.degrees(x) for x in joint_limits(panel.role)[name]))
        angles[name]=spin;grid.addWidget(spin,row,1)
        for index in (0,1):
            button=QPushButton('Capture '+('A' if index==0 else 'B'));labels[name,index]=button
            button.clicked.connect(lambda checked=False,n=name,i=index:capture(n,i));grid.addWidget(button,row,index+2)
    layout.addWidget(status)
    def save():
        try:
            joints=tuple(JointBinding(name,i,'percent' if name=='gripper' else 'degrees',
                (captures[name,0][0],captures[name,1][0]),(captures[name,0][1],captures[name,1][1])) for i,name in enumerate(JOINT_NAMES,1))
            binding=RobotBinding(panel.role,panel.session.device_id,panel.calibration.identity,joints)
            path,_=QFileDialog.getSaveFileName(dialog,'Save measured binding','','JSON (*.json)')
            if not path:return
            from pathlib import Path
            from .hardware_calibration import save_binding
            save_binding(Path(path),binding)
            panel.binding=binding;panel.binding_label.setText('Measured binding loaded');dialog.accept()
        except KeyError:status.setText('Capture both A and B for every joint.')
        except Exception as exc:status.setText(str(exc))
    button=QPushButton('Save and use measured binding');button.clicked.connect(save);layout.addWidget(button)
    return dialog
