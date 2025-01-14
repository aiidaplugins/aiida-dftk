def test_silicon_workflow(get_dftk_code, generate_structure, generate_kpoints_mesh, load_psp, submit_and_await_success):
    """
    Tests that a simple silicon SCF completes successfully and produces the expected outputs.
    """
    from aiida import orm
    from aiida_dftk.workflows.base import DftkBaseWorkChain
    from numpy.testing import assert_allclose

    builder = DftkBaseWorkChain.get_builder()
    builder.dftk.code = get_dftk_code()
    builder.dftk.structure = generate_structure("silicon_perturbed")
    builder.kpoints = generate_kpoints_mesh(3)

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

    # Disable MPI for now. If we ever enable MPI,
    # we'll need to make sure that tests can run on both GitHub Actions and locally without (too much) special setup.
    builder.dftk.metadata.options.withmpi = False

    result = submit_and_await_success(builder, timeout=600)

    output_parameters = result.outputs.output_parameters.get_dict()
    assert output_parameters["converged"]

    # Compare against values from running the test in the past, just to make sure they don't change unexpectedly.
    _REFERENCE_ENERGY = -8.4379856175524
    _REFERENCE_FORCES = [
        [-1.44715423e-02, -4.32340280e-13, -4.32937222e-13],
        [ 1.44678314e-02,  2.36668451e-13,  2.35940027e-13],
    ]
    _REFERENCE_STRESSES = [
        [-1.23236770e-04,  0.00000000e+00,  0.00000000e+00],
        [ 0.00000000e+00, -1.28905279e-04, -6.65119701e-05],
        [ 0.00000000e+00, -6.65119701e-05, -1.28905279e-04],
    ]

    assert_allclose(output_parameters["energies"]["total"], _REFERENCE_ENERGY, rtol=1e-2)
    assert_allclose(result.outputs.output_forces.get_array(), _REFERENCE_FORCES, rtol=1e-2)
    assert_allclose(result.outputs.output_stresses.get_array(), _REFERENCE_STRESSES, rtol=1e-2)
