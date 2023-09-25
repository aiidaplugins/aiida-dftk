# -*- coding: utf-8 -*-
"""Pseudopotential utility functions."""
import typing as ty

from aiida import orm
from aiida_pseudo.data.pseudo import UpfData

__all__ = ('validate_and_prepare_pseudos_inputs',)


def validate_and_prepare_pseudos_inputs(
    structure: orm.StructureData,
    pseudos: ty.Optional[ty.Dict[str, UpfData]] = None  # pylint: disable=unsubscriptable-object
) -> ty.Dict[str, UpfData]:  # pylint: disable=invalid-name
    """Validate the given pseudos mapping with respect to the given structure.

    The pseudos dictionary should now be a dictionary of UpfData nodes with the kind as linkname
    As such, if there are multiple kinds with the same element, there will be duplicate UpfData nodes
    but multiple links for the same input node are not allowed. Moreover, to couple the UpfData nodes
    to the Calculation instance, we have to go through the use_pseudo method, which takes the kind
    name as an additional parameter. When creating a Calculation through a Process instance, one
    cannot call the use methods directly but rather should pass them as keyword arguments. However,
    we can pass the additional parameters by using them as the keys of a dictionary

    :param structure: StructureData node
    :param pseudos: a dictionary where keys are the kind names and value are Psp8 nodes
    :raises: ValueError if no Psp8 is found for every element in the structure
    :returns: a dictionary of Psp8 nodes where the key is the kind name
    """

    if isinstance(pseudos, (str, orm.Str)):
        raise TypeError('you passed "pseudos" as a string - maybe you wanted to pass it as "pseudo_family" instead?')

    for kind in structure.get_kind_names():
        if kind not in pseudos:
            raise ValueError(f'no pseudo available for element {kind}')
        elif not isinstance(pseudos[kind], UpfData):
            raise ValueError(f'pseudo for element {kind} is not of type UpfData')

    return pseudos