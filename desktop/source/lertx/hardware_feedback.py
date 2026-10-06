"""Display prerequisites without weakening the serial owner's enforcement."""


def torque_summary(snapshot):
    sample=snapshot.get('sample')
    if not sample or snapshot.get('stale'):
        return 'Torque unknown — waiting for fresh readings from all six motors.'
    count=sum(bool(m['torque']) for m in sample['motors'].values())
    if count==0:return 'Torque OFF · all 6 motors — the arm can be moved by hand.'
    if count==6:return 'Torque ON · all 6 motors — the arm holds its pose.'
    return f'Torque ON · {count} of 6 motors — support the arm and release torque.'


def arming_blocker(snapshot):
    state=snapshot['state'];sample=snapshot.get('sample')
    if state=='armed':return 'Motors are enabled. Hold Move to execute targets; Release torque makes the arm free to move.'
    if state in ('connecting','arming'):return 'Wait for the current motor operation to finish.'
    if state=='calibrating':return 'Finish or cancel calibration before enabling motors.'
    if state=='fault':return 'Resolve the connection fault and reconnect: '+snapshot.get('error','')
    if state!='read-only':return 'Connect the selected arm first.'
    if not snapshot.get('calibration'):return 'Finish device setup or import this arm’s matching calibration first.'
    if not sample or snapshot.get('stale'):return 'Wait for fresh readings from all six motors. Check USB and motor power.'
    if sample.get('calibration_error'):return 'Calibration does not match the measured pose: '+sample['calibration_error']
    if not sample.get('observations'):return 'Waiting for calibrated joint readings.'
    if any(m['torque'] for m in sample['motors'].values()):return 'Support the arm and Release torque before enabling it here.'
    return ''
