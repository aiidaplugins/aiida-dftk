# Aiida_DFTK_Test
[AiiDA](https://www.aiida.net/) plugin for [DFTK](https://docs.dftk.org/stable/)
___

## Scheduled Meetings

>|                     |                 Objectives                |                                                           Coomment                                                           |
>|:-------------------:|:-----------------------------------------:|:----------------------------------------------------------------------------------------------------------------------------:|
>|    Week 1 of July   | Be   familiar with Aiida and DFTK         |  6th of July at 10am, without Prof Pizzi, Zoom link: https://epfl.zoom.us/j/69202311488?pwd=VlVRZ0ZKRzZzRFVnbE42SEF4ajJwdz09 |
>|    Week 2 of July   |           Aiida_DFTK plugin: SCF          | 11th of July at 2pm, without Prof Herbst, Zoom link: https://epfl.zoom.us/j/65737635872?pwd=M01MODJ2S0FOQm9GRGdDSU9sUTZxQT09 |
>| Second half of July | Aiida_DFTK plugin: NSCF (band & DOS PDOS) | 17th of July at 10am, Prof Herbst's Office                                                                                   |
----

## Gaols

1.	Aiida_DFTK plugin for SCF and NSCF calculations (July)- Get the structure work first rather than details
    1.	Test DFTK with some basic materials, formatting julia scripts
        1. **Parameters**:
            1.	Pseudo-dojo UPF
            2.	Encut
            3.	K-points
            4.	Fermi-Dirac smearing with parameters
            5.	Spin
    2.	{Json storing DFTK input structure}+{parameters}>{Julia script running DFTK}
    3.	Collect output and warnings (exception catch) to json
        1.	Energy (Unit conversion!)
        2.	Forces, stress (optional)
        3.	Total magnetization
    4.	Try restart from charge density with user specified k-points (for bands and DOS/PDOS)
    5.	DOS and PDOS
2.	Aiida_DFTK workflow: minimal 5 inputs with default parameters (August)
    1.	[AiiDA common workflows](https://aiida-common-workflows.readthedocs.io/en/latest/workflows/base/relax.html>)
3.	Test: 960 equation of states vs. ABINIT <https://arxiv.org/pdf/2305.17274.pdf>
4.	Structural optimization (secondary)


---


