import h5py
from aiida.orm import Dict, ArrayData
import aiida
aiida.load_profile()

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
            result[key] = _hdf5_to_dict(item)
    return result

file_path = '/home/max/Desktop/Aiida_DFTK_Test/plugin_test/aiida_dftk/examples/MoS2/compute_forces_cart.hdf5'
with h5py.File(file_path, 'r') as f:
    force_dict = _hdf5_to_dict(f)

force_array = ArrayData()
force_array.set_array('forces', force_dict['results'])
print(force_array.get_array('forces'))
