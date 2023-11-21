# -*- coding: utf-8 -*-
import json
from os import path
from tempfile import TemporaryDirectory

from aiida.common.exceptions import NotExistent
from aiida.engine import ExitCode
from aiida.orm import ArrayData, Dict
from aiida.parsers import Parser
import h5py


class DftkParser(Parser):
    """`Parser` implementation for DFTK."""
    _DEFAULT_SCFRES_SUMMARY_NAME = 'self_consistent_field.json'
    _DEFAULT_ENERGY_UNIT = 'hartree'
    _DEFAULT_FORCE_FUNCNAME = 'compute_forces_cart'
    _DEFAULT_FORCE_UNIT = 'hartree/bohr'
    _DEFAULT_STRESS_FUNCNAME = 'compute_stresses_cart'
    _DEFAULT_STRESS_UNIT = 'hartree/bohr^3'

    def parse(self, **kwargs):
        """Parse DFTK output files."""
        try:
            retrieved = self.retrieved
        except NotExistent:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        parameters = self.node.inputs.parameters.get_dict()
        retrieve_list = self.node.get_attribute('retrieve_list')
        with TemporaryDirectory() as dirpath:
            retrieved.copy_tree(dirpath)

            #catch exceptions from SCF, forces, stresses
            # TODO: handle exceptions for future supported postscf (bands, dos)
            if self._DEFAULT_SCFRES_SUMMARY_NAME in retrieve_list:
                file_path = path.join(dirpath, self._DEFAULT_SCFRES_SUMMARY_NAME)
                exit_code = self._parse_output_parameters(file_path)
                if exit_code is not None:
                    return exit_code

            if f'{self._DEFAULT_FORCE_FUNCNAME}.hdf5' in retrieve_list:
                file_path = path.join(dirpath, f'{self._DEFAULT_FORCE_FUNCNAME}.hdf5')
                exit_code = self._parse_output_forces(file_path)
                if exit_code is not None:
                    return exit_code

            if f'{self._DEFAULT_STRESS_FUNCNAME}.hdf5' in retrieve_list:
                file_path = path.join(dirpath, f'{self._DEFAULT_STRESS_FUNCNAME}.hdf5')
                exit_code = self._parse_output_stresses(file_path)
                if exit_code is not None:
                    return exit_code

        return ExitCode(0)

    def _parse_output_parameters(self, file_path):
        """
        Parse the output file and return a dictionary with results.

        :param output_file: Output file path
        :return: Dictionary with results
        """

        with open(file_path, 'r') as file:
            data = json.load(file)

        # Ignore the 'occupation' and 'eigenvalues' keys
        # TODO: add back for bands after implementation in DFTK
        data.pop('occupation', None)
        data.pop('eigenvalues', None)

        # Rename the special keys
        data['norm_delta_rho'] = data.pop('norm_Δρ', None)
        data['fermi_level'] = data.pop('εF', None)

        # Add energy units
        for key in list(data['energies'].keys()):
            unit_key = f'{key}_unit'
            data['energies'][unit_key] = self._DEFAULT_ENERGY_UNIT

        data['fermi_level_unit'] = self._DEFAULT_ENERGY_UNIT

        # Check for 'converged'
        if not data.get('converged'):
            return self.exit_codes.ERROR_SCF_CONVERGENCE_NOT_REACHED

        self.out('output_parameters', Dict(dict=data))

    def _parse_output_forces(self, file_path):
        """
        Parse the output file and return a dictionary with results.

        :param output_file: Output file path
        :return: Dictionary with results
        """
        with h5py.File(file_path, 'r') as f:
            force_dict = DftkParser._hdf5_to_dict(f)

        force_array = ArrayData()
        force_array.set_array('output_forces', force_dict['results'])
        self.out('output_forces', force_array)

        # TODO!!!: add a check for the forces array agrees with number of atoms

    def _parse_output_stresses(self, file_path):
        """
        Parse the output file and return a dictionary with results.

        :param output_file: Output file path
        :return: Dictionary with results
        """
        with h5py.File(file_path, 'r') as f:
            stress_dict = DftkParser._hdf5_to_dict(f)

        stress_array = ArrayData()
        stress_array.set_array('output_stresses', stress_dict['results'])
        self.out('output_stresses', stress_array)

    @staticmethod
    def _hdf5_to_dict(hdf5_file):
        """
        Convert an HDF5 file to a Python dictionary.

        :param hdf5_file: File or group object from h5py (HDF5 file handle or subgroup)
        :return: Dictionary representation of the HDF5 file or group.
        """
        result = {}

        for key, item in hdf5_file.items():
            if isinstance(item, h5py.Dataset):  # item is a dataset
                value = item[()]
                if isinstance(value, bytes):  # Check if the value is bytes and decode if necessary
                    value = value.decode('utf-8')
                result[key] = value
            elif isinstance(item, h5py.Group):  # item is a group
                result[key] = DftkParser._hdf5_to_dict(item)
        return result
