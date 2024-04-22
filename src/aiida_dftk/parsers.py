# -*- coding: utf-8 -*-
"""`Parser` implementation for DFTK."""
import json
from os import path
import pathlib as pl
from tempfile import TemporaryDirectory

from aiida.common.exceptions import NotExistent
from aiida.engine import ExitCode
from aiida.orm import ArrayData, Dict
from aiida.parsers import Parser

from aiida_dftk.calculations import DftkCalculation

import h5py


class DftkParser(Parser):
    """`Parser` implementation for DFTK."""

    _DEFAULT_SCFRES_SUMMARY_NAME = 'self_consistent_field.json'
    _DEFAULT_ENERGY_UNIT = 'hartree'
    _DEFAULT_FORCE_FUNCNAME = 'compute_forces_cart'
    _DEFAULT_FORCE_UNIT = 'hartree/bohr'
    _DEFAULT_STRESS_FUNCNAME = 'compute_stresses_cart'
    _DEFAULT_STRESS_UNIT = 'hartree/bohr^3'
    _DEFAULT_BANDS_FUNCNAME = 'compute_bands'
    _DEFAULT_BANDS_UNIT = 'hartree'

    def parse(self, **kwargs):
        """Parse DFTK output files."""
        try:
            retrieved = self.retrieved
        except NotExistent:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        retrieve_list = self.node.get_attribute('retrieve_list')
        with TemporaryDirectory() as dirpath:
            retrieved.copy_tree(dirpath)

            # if ran_out_of_walltime (terminated illy)
            if self.node.exit_status == DftkCalculation.exit_codes.ERROR_SCHEDULER_OUT_OF_WALLTIME.status:
                # if _DEFAULT_SCFRES_SUMMARY_NAME is not in the list retrieved.list_object_names(), SCF terminated illy
                if self._DEFAULT_SCFRES_SUMMARY_NAME not in retrieved.list_object_names():
                    return self.exit_codes.ERROR_SCF_OUT_OF_WALLTIME
                # POSTSCF terminated illy
                else:
                    return self.exit_codes.ERROR_POSTSCF_OUT_OF_WALLTIME
        
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
                
            #TODO: parser for bands results
            # if f'{self._DEFAULT_BANDS_FUNCNAME}.json' in retrieve_list:
            #     file_path = path.join(dirpath, f'{self._DEFAULT_BANDS_FUNCNAME}.json')
            #     exit_code = self._parse_output_bands(file_path)
            #     if exit_code is not None:
            #         return exit_code

        return ExitCode(0)

    def _parse_output_parameters(self, file_path):
        """Parse the output file and return a dictionary with results.

        :param output_file: Output file path
        :return: Dictionary with results
        """

        with open(file_path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)

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

        self.out('output_parameters', Dict(dict=data))
        
        # Check for 'converged'
        if not data.get('converged'):
            return self.exit_codes.ERROR_SCF_CONVERGENCE_NOT_REACHED

        return None

    def _parse_output_forces(self, file_path):
        """Parse the output file and return a dictionary with results.

        :param output_file: Output file path
        :return: Dictionary with results
        """
        if not pl.Path(file_path).exists():
            return self.exit_codes.ERROR_MISSING_FORCES_FILE

        with h5py.File(file_path, 'r') as h5file:
            force_dict = DftkParser._hdf5_to_dict(h5file)

        # TODO: add a check for the forces array agrees with number of atoms
        force_array = ArrayData()
        force_array.set_array('output_forces', force_dict['results'])
        self.out('output_forces', force_array)
        return None

    def _parse_output_stresses(self, file_path):
        """Parse the output file and return a dictionary with results.

        :param output_file: Output file path
        :return: Dictionary with results
        """
        if not pl.Path(file_path).exists():
            return self.exit_codes.ERROR_MISSING_STRESSES_FILE

        with h5py.File(file_path, 'r') as h5file:
            stress_dict = DftkParser._hdf5_to_dict(h5file)

        stress_array = ArrayData()
        stress_array.set_array('output_stresses', stress_dict['results'])
        self.out('output_stresses', stress_array)
        return None

    @staticmethod
    def _hdf5_to_dict(hdf5_file):
        """Convert an HDF5 file to a Python dictionary.

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
