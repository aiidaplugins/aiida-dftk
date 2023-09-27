# 2. Running an Example DFTK Calculation on Silicon using AiiDA

This tutorial provides step-by-step instructions to run a DFTK calculation on a silicon crystal using AiiDA. We'll cover the following components:

1. **Structure**: Setting up the silicon crystal structure.
2. **Code**: Loading the DFTK code.
3. **Pseudopotentials**: Specifying the pseudopotentials for silicon.
4. **K-points**: Defining the k-point mesh for the calculation.
5. **Parameters**: Setting up the computational parameters.

---

## Preparing the Environment

Before proceeding, make sure you've completed the [development environment setup tutorial](#). This will ensure that you have both the Julia and Python sides ready for DFTK calculations through AiiDA.

---

## Step 1: Setting Up the Structure

The structure of silicon will be read from a CIF file.

```python
from aiida import orm

cif = orm.CifData(file="/path/to/your/Si.cif")
structure = cif.get_structure()
```

---

## Step 2: Loading the DFTK Code

Assuming you've already set up the DFTK code in AiiDA (as per the development environment setup), you can load it as follows:

```python
code = orm.load_code('DFTK@local_direct')
```

---

## Step 3: Specifying Pseudopotentials

You can specify the pseudopotentials using a pre-loaded pseudopotential group. Here, we assume that you have a group named "PseudoDojo/0.4/PBE/SR/standard/upf".

```python
ppf = load_group("PseudoDojo/0.4/PBE/SR/standard/upf")
pseudos = ppf.get_pseudos(structure=structure)
```

---

## Step 4: Setting Up K-points

Define the k-point mesh for the calculation:

```python
kpoints = orm.KpointsData()
kpoints.set_cell_from_structure(structure)
kpoints.set_kpoints_mesh([2, 2, 2])
```

---

## Step 5: Setting Up Parameters

The computational parameters for the DFTK calculation are specified using an `orm.Dict` object in AiiDA. Below is a breakdown of the parameters you can set:

```python
parameters = orm.Dict({
    "model_kwargs": {
        "xc": [":gga_x_pbe", ":gga_c_pbe"],  # Exchange-correlation functional
        "temperature": 0.001,  # Electronic temperature in Hartree
        "smearing": {
            "$symbol": "Smearing.Gaussian"  # Type of smearing
        }
    },
    "basis_kwargs": {
        "Ecut": 6  # Plane-wave cutoff energy in Hartree
    },
    "scf": {
        "$function": "self_consistent_field",  # SCF calculation function
        "checkpointfile": "scfres.jld2",  # File to save the SCF results
        "$kwargs": {
            "is_converged": {
                "$symbol": "ScfConvergenceEnergy",  # Convergence criterion
                "$args": 1.0e-2  # Convergence threshold
            },
            "maxiter": 100  # Maximum SCF iterations
        }
    },
    "postscf": [
        {
            "$function": "compute_forces_cart"  # Compute Cartesian forces
        },
        {
            "$function": "compute_stresses_cart"  # Compute Cartesian stresses
        }
    ]
})
```

### Explanation of Parameters

- `model_kwargs`: Keywords arguments for setting up the DFT model. It includes the exchange-correlation functional (`xc`) (any functionals supported by [Libxc](https://www.tddft.org/programs/libxc/functionals/)), electronic temperature (`temperature`), and the type of electronic smearing (`smearing`).

- `basis_kwargs`: Contains parameters for the plane-wave basis set. Here, `Ecut` specifies the plane-wave cutoff energy in Hartree.

- `scf`: Parameters related to the self-consistent field (SCF) calculations. It includes the function to perform SCF (`$function`), a file to save the SCF results (`checkpointfile`), and additional arguments like convergence criteria (`is_converged`) and maximum iterations (`maxiter`).

- `postscf`: A list of functions to perform post-SCF calculations. Currently, only Cartesian forces (`compute_forces_cart`) and stresses (`compute_stresses_cart`) are supported.



---


## Running the Calculation

Run the DFTK calculation using AiiDA's `run` method:

```python
from aiida import engine
from aiida.plugins import CalculationFactory

DFTKCalculation = CalculationFactory('dftk')

parameters_dict = {
    'code': code,
    'structure': structure,
    'pseudos': pseudos,
    'kpoints': kpoints,
    'parameters': parameters,
    'metadata': {
        'options': {
            'withmpi': False,
            'resources': {
                'num_machines': 1,
                'num_mpiprocs_per_machine': 1,
            }
        }
    }
}

result = engine.run(DFTKCalculation, **parameters_dict)
```

---

## Visualizing the Provenance Graph

After execution, generate a provenance graph for the calculation with the following command:

```bash
verdi node graph generate [PK of your process]
```
The graph should have 5 data nodes (`InstalledCode`, `UpfData`, `StructureData`, `KpointsData`, `Input_parameters`) as inputs to the process node and 5 output data nodes (`RemoteData`, `RetrievedFolder`, `Output_parameters`, `Output_forces`, `Output_stresses`).
