import sys

if sys.path[0] != '/etc/dsiprouter/gui':
    sys.path.insert(0, '/etc/dsiprouter/gui')

from util.ipc import STATE_SHMEM_NAME, getSharedMemoryDict
from util.pyasync import mpexec
from modules.api.licensemanager.classes import WoocommerceLicense, AES_CTR
import settings


# must be defined here or mpexec will fail to copy the func to child procs
def __getLicense(license):
    return WoocommerceLicense(key_combo=license, decrypt=True)

def quickLoadLicenses(keystore):
    # task for parallel processing (will send external requests on instantiation)

    return mpexec(__getLicense, ([x] for x in keystore.values()))

def licenseDictToStateDict(keystore):
    """
    Transform the license store into a lookup dict based on key

    :param keystore:    the key store
    :type keystore:     dict
    :return:            keys formatted as a status lookup dict
    :rtype:             dict
    """

    return {lc.license_key: lc for lc in quickLoadLicenses(keystore)}

def syncLicensesToGlobalState():
    getSharedMemoryDict(STATE_SHMEM_NAME)['dsip_license_store'] = licenseDictToStateDict(settings.DSIP_LICENSE_STORE)

def getLicenseStatusFromStateDict(license_state, tag):
    """
    Get license status given the license state dict and a license tag

    :param license_state:   the license key store in global state
    :type license_state:    dict
    :param tag:             license tag to lookup
    :type tag:              str
    :return:                status of first license with that tag (valid licenses have priority)
    :rtype:                 int

    the license status corresponds to::
        -1  ==  an unknown error occurred looking up the status
        0   ==  no license present
        1   ==  license present but not active
        2   ==  license present but associated with another machine
        3   ==  license present and valid
    """

    res = [lc for lc in license_state.values() if tag in lc.tags]
    if len(res) == 0:
        return 0
    lic = next((lc for lc in res if lc.valid), None)
    if lic is not None:
        return 3
    lic = res[0]
    if not lic.machine_match:
        return 2
    if not lic.active:
        return 1
    return -1

def searchLicenses(license_key=None, key_combo=None, decrypt=False):
    """
    Search licenses from the global state

    :param license_key: license key to lookup
    :type license_key:  str
    :param key_combo:   license tag to lookup
    :type key_combo:    str
    :param decrypt:     whether to return only valid/invalid licenses
    :type decrypt:      bool
    :return:            matching licenses
    :rtype:             list
    """

    if license_key is None and key_combo is None:
        return list(getSharedMemoryDict(STATE_SHMEM_NAME)['dsip_license_store'].values())
    if license_key is not None:
        if key_combo is not None:
            raise ValueError('license_key and key_combo are mutually exclusive')

        if isinstance(license_key, str):
            if len(license_key) == 0:
                raise ValueError('license_key must not be empty')
            if decrypt:
                license_key = AES_CTR.decrypt(license_key)
        elif isinstance(license_key, bytes):
            if len(license_key) == 0:
                raise ValueError('license_key must not be empty')
            if decrypt:
                license_key = AES_CTR.decrypt(license_key)
            else:
                license_key = license_key.decode('utf-8')
        else:
            raise ValueError('license_key must be a string or byte string')
    elif key_combo is not None:
        if isinstance(key_combo, str):
            if len(key_combo) == 0:
                raise ValueError('key_combo must not be empty')
            if decrypt:
                key_combo = AES_CTR.decrypt(key_combo.encode('utf-8'))
        elif isinstance(key_combo, bytes):
            if len(key_combo) == 0:
                raise ValueError('key_combo must not be empty')
            if decrypt:
                key_combo = AES_CTR.decrypt(key_combo)
            else:
                key_combo = key_combo.decode('utf-8')
        else:
            raise ValueError('key_combo must be a string or byte string')

        try:
            license_key = key_combo[:-WoocommerceLicense.MACHINE_ID_LEN]
        except IndexError:
            raise ValueError('key_combo is invalid')
    try:
        return [getSharedMemoryDict(STATE_SHMEM_NAME)['dsip_license_store'][license_key]]
    except KeyError:
        return []


def getLicenseStatus(tag):
    """
    Get license status from the global state by tag

    :param tag: license tag to lookup
    :type tag:  str
    :return:    status of first license with that tag (valid licenses have priority)
    :rtype:     int

    the license status corresponds to::

        0 == no license present
        1 == license present but not valid
        2 == license present but associated with another machine
        3 == license present and valid
    """

    res = [lc for lc in getSharedMemoryDict(STATE_SHMEM_NAME)['dsip_license_store'].values() if tag in lc.tags]
    if len(res) == 0:
        return 0
    lic = next((lc for lc in res if lc.valid), None)
    if lic is not None:
        return 3
    lic = res[0]
    if not lic.machine_match:
        return 2
    if not lic.active:
        return 1
    raise Exception('could not determine status of license')
