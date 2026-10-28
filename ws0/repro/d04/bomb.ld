// Guard Door Interlock : BOMB baseline
// Defect: machine_run omits the safety relay check entirely
OTE(safety_relay) := XIC(guard_closed) * XIO(estop_pressed) ;
OTE(machine_run) := XIC(req_run) ;
