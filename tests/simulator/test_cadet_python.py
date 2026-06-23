import subprocess
import sys
import textwrap


REPRODUCER_SCRIPT = textwrap.dedent("""
    import warnings
    from CADETProcess.processModel import (
        ComponentSystem, Inlet, Outlet, LumpedRateModelWithoutPores,
        MassActionLaw, FlowSheet, Process
    )
    from CADETProcess.simulator import Cadet

    component_system = ComponentSystem(1)
    inlet = Inlet(component_system, name='inlet')
    column = LumpedRateModelWithoutPores(component_system, name='column')
    outlet = Outlet(component_system, name='outlet')

    reaction_system = MassActionLaw(component_system)
    reaction_system.add_reaction(indices=[0], coefficients=[-1], k_fwd=1e-3, k_bwd=0)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        column.particle_reaction_model = reaction_system

    flow_sheet = FlowSheet(component_system)
    flow_sheet.add_unit(inlet)
    flow_sheet.add_unit(column)
    flow_sheet.add_unit(outlet)
    flow_sheet.add_connection(inlet, column)
    flow_sheet.add_connection(column, outlet)

    process = Process(flow_sheet, 'mre')
    column.length = 0.1
    column.diameter = 0.01
    column.axial_dispersion = 1e-7
    column.total_porosity = 1
    column.discretization.ncol = 20

    inlet.flow_rate = [1e-6, 0, 0, 0]
    process.cycle_time = 100
    process.add_event('start', 'flow_sheet.inlet.c', [1.0], 0)
    process.add_event('stop', 'flow_sheet.inlet.c', [0.0], 10)

    simulator = Cadet()
    simulator.use_dll = True

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        simulator.simulate(process)
""")


def run_fresh_process(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )


def test_particle_reaction_model_on_lrmp_without_solid_phase_is_deterministic():
    n_runs = 10

    results = [run_fresh_process(REPRODUCER_SCRIPT) for _ in range(n_runs)]
    failures = [result for result in results if result.returncode != 0]

    assert not failures, (
        f"{len(failures)}/{n_runs} fresh-process runs failed.\n\n"
        "First failing stderr:\n"
        f"{failures[0].stderr if failures else ''}"
    )