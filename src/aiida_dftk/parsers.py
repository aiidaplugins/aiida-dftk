# -*- coding: utf-8 -*-
"""`Parser` implementation for DFTK."""
import json
import pathlib as pl
import numpy as np

from aiida.engine import ExitCode
from aiida.orm import ArrayData, Dict
from aiida.parsers import Parser
from aiida.plugins import DataFactory


from aiida_dftk.calculations import DftkCalculation

import h5py

# DataFactory is used to create the BandsData object
BandsData = DataFactory('core.array.bands')

class DftkParser(Parser):
    """`Parser` implementation for DFTK."""

    # TODO: DEFAULT_ prefix should be removed. I don't think that these names can be changed.
    _DEFAULT_ENERGY_UNIT = 'hartree'
    _DEFAULT_FORCE_FUNCNAME = 'compute_forces_cart'
    _DEFAULT_FORCE_UNIT = 'hartree/bohr'
    _DEFAULT_STRESS_FUNCNAME = 'compute_stresses_cart'
    _DEFAULT_STRESS_UNIT = 'hartree/bohr^3'
    _DEFAULT_BANDS_FUNCNAME = 'compute_bands'
    _DEFAULT_BANDS_UNIT = 'hartree'

    def parse(self, **kwargs):
        """Parse DFTK output files."""
        # if ran_out_of_walltime (terminated illy)
        if self.node.exit_status == DftkCalculation.exit_codes.ERROR_SCHEDULER_OUT_OF_WALLTIME.status:
            # if SCF summary file is not in the list of retrieved files, SCF terminated illy
            if DftkCalculation.SCFRES_SUMMARY_NAME not in self.retrieved.list_object_names():
                return self.exit_codes.ERROR_SCF_OUT_OF_WALLTIME
            # POSTSCF terminated illy
            else:
                return self.exit_codes.ERROR_POSTSCF_OUT_OF_WALLTIME
        
        # Check error file
        try:
            errors_log = self.retrieved.base.repository.get_object_content(DftkCalculation.LOGFILE)
            if "Imports succeeded" not in errors_log:
                return self.exit_codes.ERROR_PACKAGE_IMPORT_FAILED
        except FileNotFoundError:
            return self.exit_codes.ERROR_PACKAGE_IMPORT_FAILED

        if "Finished successfully" not in errors_log:
            return self.exit_codes.ERROR_UNSPECIFIED

        # Check retrieve list to know which files the calculation is expected to have produced.
        try:
            self._parse_optional_result(
                DftkCalculation.SCFRES_SUMMARY_NAME,
                self.exit_codes.ERROR_MISSING_SCFRES_FILE,
                self._parse_output_parameters,
            )

            self._parse_optional_result(
                f'{self._DEFAULT_FORCE_FUNCNAME}.hdf5',
                self.exit_codes.ERROR_MISSING_FORCES_FILE,
                self._parse_output_forces,
            )

            self._parse_optional_result(
                f'{self._DEFAULT_STRESS_FUNCNAME}.hdf5',
                self.exit_codes.ERROR_MISSING_STRESSES_FILE,
                self._parse_output_stresses,
            )

            self._parse_optional_result(
                f'{self._DEFAULT_BANDS_FUNCNAME}.json',
                self.exit_codes.ERROR_MISSING_BANDS_FILE,
                self._parse_output_bands,
            )
        except ParsingFailedException as e:
            return e.exitcode

        return ExitCode(0)

    def _parse_optional_result(self, file_name, missing_file_exitcode, parser):
        # Files passed to the CalcInfo to be retrieved
        retrieve_list = self.node.base.attributes.get('retrieve_list')
        # Files that were actually retrieved
        retrieved_files = self.retrieved.base.repository.list_object_names()

        if file_name in retrieve_list:
            if file_name not in retrieved_files:
                raise ParsingFailedException(missing_file_exitcode)
            with self.retrieved.base.repository.as_path(file_name) as file_path:
                parser(file_path)

    def _parse_output_parameters(self, file_path):
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
        with h5py.File(file_path, 'r') as h5file:
            force_dict = DftkParser._hdf5_to_dict(h5file)

        # TODO: add a check for the forces array agrees with number of atoms
        force_array = ArrayData()
        force_array.set_array('output_forces', force_dict['results'])
        self.out('output_forces', force_array)
        return None

    def _parse_output_stresses(self, file_path):
        with h5py.File(file_path, 'r') as h5file:
            stress_dict = DftkParser._hdf5_to_dict(h5file)

        stress_array = ArrayData()
        stress_array.set_array('output_stresses', stress_dict['results'])
        self.out('output_stresses', stress_array)
        return None
    
    def _parse_output_bands(self, file_path):
        if not pl.Path(file_path).exists():
            return self.exit_codes.ERROR_MISSING_BANDS_FILE

        with open(file_path, 'r', encoding='utf-8') as json_file:
            bands_dict = json.load(json_file)
        
        if bands_dict['diagonalization']['converged'] is False:
            return self.exit_codes.ERROR_BANDS_CONVERGENCE_NOT_REACHED
        
        bands_data = BandsData()
        kpath = bands_dict['kcoords']
        eigen_array = np.array(bands_dict['eigenvalues'])
        nspin = bands_dict['n_spin_components']
        nkpoints = bands_dict['n_kpoints']
        nbands = bands_dict['n_bands']

        bands = eigen_array.reshape(nspin, nkpoints, nbands)

        bands_data.set_kpoints(kpoints=kpath)
        bands_data.set_bands(bands, units=self._DEFAULT_BANDS_UNIT)
        self.out('output_bands', bands_data)

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

class ParsingFailedException(Exception):
    def __init__(self, exitcode: ExitCode):
        super().__init__(exitcode)
        self.exitcode = exitcode
