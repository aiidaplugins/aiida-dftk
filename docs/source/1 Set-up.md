# 1. Setting Up the Development Environment for AiidaDFTk Calculations

In this tutorial, we will guide you through setting up a development environment for running [DFTk](https://docs.dftk.org/stable/) calculations using AiiDA. The tutorial is divided into two main sections:
1. **Julia Side**: Creating a Julia project and installing AiidaDFTK.
2. **Python Side**: Setting up aiida-core, installing the aiida-DFTK plugin, defining an AiiDA computer, code, and managing pseudopotentials.

---

## Part 1: Julia Side

### Preliminary: Installing Julia
If you don't yet have Julia installed, first [download the Julia binaries](https://julialang.org/downloads/) and follow the [installation instructions](https://julialang.org/downloads/platform/).

### Steps to Set Up a Julia Project

1. **Open Julia Terminal**: Launch Julia from your computer's application menu or terminal.
2. **Activate a New Environment**: In the Julia REPL, create a new environment (essentially a new Julia project) using the following commands:
    ```julia
    using Pkg
    Pkg.activate("path/to/new/environment")
    ```
    Replace `path/to/new/environment` with the directory where you wish to create the new environment. This will generate a folder containing `Project.toml` and `Manifest.toml` files.
3. **Install AiidaDFTK**: While still in the Julia REPL, initialize the project by adding packages you'll need. For this tutorial, we start with `AiidaDFTK`.
    ```julia
    Pkg.add("AiidaDFTK")
    ```

The new Julia project is now ready and includes `AiidaDFTK` and its dependency `DFTK`. You can now proceed with DFTk calculations in this isolated environment.

---

## Part 2: Python Side

### Step 1: Setting Up aiida-core
Follow the [official aiida-core setup tutorial](https://aiida.readthedocs.io/projects/aiida-core/en/latest/intro/get_started.html). For simplicity, this tutorial assumes the use of the QuantumMobile Virtual Machine, which comes with AiiDA pre-installed.

To use AiiDA, we need to activate the AiiDA environment by
```bash
workon aiida
```

### Step 2: Installing the aiida-DFTK Plugin
Clone the aiida-DFTK plugin repository from GitHub and install it locally using the following commands:
```bash
git clone https://github.com/azadoks/aiida-dftk.git
cd aiida-dftk
git checkout Aiida_plugin
pip install -e .
```

### Step 3: Defining an AiiDA Computer
For a detailed guide on defining a new computer in AiiDA, consult the [official AiiDA tutorial](https://aiida.readthedocs.io/projects/aiida-core/en/v1.0.1/get_started/computers.html). In the QuantumMobile VM, two local computers are pre-configured:
```
* local_direct
* local_slurm
```

### Step 4: Registering an AiiDA Code
DFTK, when run through AiidaDFTK, should be registered as a code in the AiiDA database. This can be done using:
```bash
verdi code setup
```
Provide the path to the Julia executable, and specify the default calculation input plugin. In the QuantumMobile VM, the path to the Julia executable is `/usr/bin/julia`, and the default calculation input plugin is `dftk`.
In the "prepend text" field during setup, export the absolute path to the Julia project where `AiidaDFTK` is installed. For example:
```bash
export JULIA_PROJECT="/path/to/your/AiidaDFTK/project"
```

### Step 5: Managing Pseudopotentials
DFTK supports both HGH and UPF pseudopotentials. For realistic calculations, UPF format is recommended. We suggest using pseudo-dojo, which can be installed using the aiida-pseudo plugin. Follow this [detailed tutorial](https://aiida-pseudo.readthedocs.io/en/latest/) for more information. Here's how to install pseudo-dojo 0.5 PBE pseudopotentials with scalar relativistic effects in UPF format:
```bash
aiida-pseudo install pseudo-dojo --v 0.5 -x PBE -r SR -f upf
```

---

Congratulations! You've successfully set up your development environment for AiidaDFTk and are ready to proceed with your calculations.
