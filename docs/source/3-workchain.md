# 3. Running an Example DFTK Calculation on Silicon using AiiDA's DftkBaseWorkChain

This tutorial guides you through the process of running a DFTK calculation on a silicon crystal using AiiDA's `DftkBaseWorkChain`. The tutorial covers:

1. **Structure**: Setting up the silicon crystal structure.
2. **Code**: Loading the DFTK code.
3. **Pseudopotentials**: Specifying pseudopotentials for silicon.
4. **K-points**: Defining the k-point mesh for the calculation.
5. **Parameters**: Setting up computational parameters.

---

## Preparing the Environment

Before proceeding, make sure you've completed the [development environment setup tutorial](#). This ensures that both the Julia and Python sides are ready for DFTK calculations through AiiDA.

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


## Step 4: K-points in base_parameters_dict

In the `DftkBaseWorkChain`, k-points can be specified directly in the `base_parameters_dict` using either the `kpoints` or `kpoints_distance` keys.

To specify a k-point mesh:

```python
kpoints = orm.KpointsData()
kpoints.set_cell_from_structure(structure)
kpoints.set_kpoints_mesh([2, 2, 2])
```

To specify k-points by distance:

```python
kpoints_distance = orm.Float(0.6)
```

---

## Step 5: Setting Up Parameters

Specify computational parameters for the DFTK calculation.

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

---

## Running the Calculation with DftkBaseWorkChain

Execute the DFTK calculation using the `DftkBaseWorkChain`.

```python
from aiida import engine
from aiida_dftk.workflows.base import DftkBaseWorkChain

base_parameters_dict = {
  'kpoints': kpoints,  # or 'kpoints_distance': kpoints_distance
  'dftk': {
    'code': code,
    'structure': structure,
    'pseudos': pseudos,
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
}

result = engine.run(DftkBaseWorkChain, **base_parameters_dict)
```

---

## Visualizing the Provenance Graph

After execution, generate a provenance graph for the calculation with the following command:

```bash
verdi node graph generate [PK of your process]
```

The graph should have 7 data nodes (`InstalledCode`, `UpfData`, `StructureData`, `KpointsData`, `Input_parameters`, `max_iterations`, `clean_directory`) as inputs to 2 process nodes and 5 output data nodes (`RemoteData`, `RetrievedFolder`, `Output_parameters`, `Output_forces`, `Output_stresses`).
