def test_silicon_workflow(get_dftk_code, generate_structure, generate_kpoints_mesh, load_psp, submit_and_await_success):
    """
    Tests that a simple silicon SCF completes successfully and produces the expected outputs.
    """
    from aiida import orm
    from aiida_dftk.workflows.base import DftkBaseWorkChain

    builder = DftkBaseWorkChain.get_builder()
    builder.dftk.code = get_dftk_code()
    builder.dftk.structure = generate_structure("silicon")
    builder.kpoints = generate_kpoints_mesh(4)

    builder.dftk.pseudos.Si = load_psp("Si")

    builder.dftk.parameters = orm.Dict({
        "model_kwargs": {
            "functionals": [":gga_x_pbe", ":gga_c_pbe"],  # Exchange-correlation functional
            "temperature": 0.001,                # Electronic temperature
            "smearing": {
                "$symbol": "Smearing.Gaussian"   # Type of smearing
            }
        },
        "basis_kwargs": {
            "Ecut": 10  # Plane-wave cutoff energy
        },
        "scf": {
            "$function": "self_consistent_field",  # Single-point SCF
            "checkpointfile": "scfres.jld2",  # Checkpoint and output file
            "$kwargs": {
                "tol": 1e-4,    # Convergence tolerance
                "maxiter": 100  # Maximum SCF iterations
            }
        },
        "postscf": [
            {
                "$function": "compute_forces_cart"
            },
            {
                "$function": "compute_stresses_cart"
            },
        ]
    })

    result = submit_and_await_success(builder, timeout=180)

    assert result.outputs.output_parameters.get_dict()["converged"]
    assert result.outputs.output_forces.get_array().shape == (2, 3)
    assert result.outputs.output_stresses.get_array().shape == (3, 3)