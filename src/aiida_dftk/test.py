{
    "model_kwargs": {
        "xc": [
            ":gga_x_pbe",
            ":gga_c_pbe"
        ],
        "temperature": 0.001,
        "smearing": {
            "$symbol": "Smearing.Gaussian"
        }
    },
    "basis_kwargs": {
        "Ecut": 30
    },
    "scf": {
        "$function": "self_consistent_field",
        "checkpointfile": "scfres.jld2",
        "$kwargs": {
            "mixing": {
                 "$symbol": "KerkerDosMixing"
            },
            "is_converged": {
                 "$symbol": "ScfConvergenceEnergy",
                 "$args": 1.0e-6
            }
        }
    },
    "postscf": [
        {
            "$function": "compute_forces_cart"
        }
    ]
}
