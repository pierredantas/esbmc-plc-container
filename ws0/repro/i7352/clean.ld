// Guard Door Interlock : CLEAN baseline
OTE(safety_relay) := XIC(guard_closed) * XIO(estop_pressed) ;
OTE(machine_run) := XIC(req_run) * XIC(safety_relay) ;
