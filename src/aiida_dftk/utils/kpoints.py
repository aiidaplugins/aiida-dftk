# -*- coding: utf-8 -*-
"""k-point utility functions."""
from aiida import orm
from aiida.engine import calcfunction
import numpy as np

__all__ = ('create_kpoints_from_distance',)


@calcfunction
def create_kpoints_from_distance(structure: orm.StructureData, distance: orm.Float) -> orm.KpointsData:
    """Generate a uniformly spaced kpoint mesh for a given structure.

    The spacing between kpoints in reciprocal space is guaranteed to be at least the defined distance.

    :param structure: the StructureData to which the mesh should apply
    :param distance: a Float with the desired distance between kpoints in reciprocal space
    :returns: a KpointsData with the generated mesh
    """
    epsilon = 1E-5

    kpoints = orm.KpointsData()
    kpoints.set_cell_from_structure(structure)
    kpoints.set_kpoints_mesh_from_density(distance.value)

    lengths_vector = [np.linalg.norm(vector) for vector in structure.cell]
    lengths_kpoint = kpoints.get_kpoints_mesh()[0]

    is_symmetric_cell = all(abs(length - lengths_vector[0]) < epsilon for length in lengths_vector)
    is_symmetric_mesh = all(length == lengths_kpoint[0] for length in lengths_kpoint)

    # If the vectors of the cell all have the same length, the kpoint mesh should be isotropic as well
    if is_symmetric_cell and not is_symmetric_mesh:
        nkpoints = max(lengths_kpoint)
        kpoints.set_kpoints_mesh([nkpoints, nkpoints, nkpoints])

    return kpoints
