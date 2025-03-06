# -*- coding: utf-8 -*-

import logging
import os
import yaml


logger = logging.getLogger(__name__)
cfg = None


def get_config():
    """Returns the object with the configuration"""
    global cfg
    if cfg is None:
        cfg = Configuration()
    return cfg


class Configuration():
    """Class for reading a yaml configuration file"""
    _cfg = dict()  # the configuration dictionary
    _filename = 'config.yaml'  # filename to read the configuration from
    _is_changed = False  # indicates whether the config was changed since loading

    def __init__(self, *args, **kw):
        pass
        #self._cfg = dict(*args, **kw);

    @property
    def cfg(self):
        return self._cfg

    def __getitem__(self, key):
        return self._cfg[key]

    def __iter__(self):
        return iter(self._cfg)

    def __len__(self):
        return len(self._cfg)

    @property
    def filename(self):
        return self._filename

    @property
    def filedir(self):
        return os.path.dirname(self._filename)

    def set_filename(self, filename):
        """Sets the file to read the configuration from"""
        self._filename = filename

    def load_config(self, filename=None):
        """Loads the configuration from file and stores it in the class"""
        if filename is not None:
            self.set_filename(filename)
        try:
            with open(self._filename, 'r') as ymlfile:
                self._cfg = yaml.load(ymlfile, Loader=yaml.SafeLoader)
        except FileNotFoundError:
            logger.warning(f'Config file [{self._filename}] not found; just using defaults')
        if self._cfg is None:
            self._cfg = dict()  # cover the case of an empty file
        self._is_changed = False

    def save_config(self, filename=None):
        """Saves the current configuration to file"""
        if filename is None:
            filename = self._filename
        if not self._is_changed:
            logger.debug(f'Nothing changed; not saving config file [{filename}]')
            return False
        logger.info('Saving config file [{0}]'.format(filename))
        try:
            with open(filename, 'w') as ymlfile:
                yaml.dump(self._cfg, ymlfile, default_flow_style=False)
        except OSError as e:
            logger.warning(f'Could not write config file [{filename}], [{str(e)}]')
        self._is_changed = False
        return True

    def get(self, itemname, default=None):
        """Return a specific item from the configuration or the provided default value if not present (low level)"""
        return self._cfg.get(itemname, default)

    def get_item(self, itemname, default=None):
        """Return a specific item from the configuration or the provided default value if not present"""
        parts = itemname.split('.')
        cfg = self._cfg
        for part in parts:
            cfg_new = cfg.get(part, dict())
            if part.isnumeric() and isinstance(cfg_new, dict) and (len(cfg_new) == 0):
                cfg_new = cfg.get(float(part), dict())
            cfg = cfg_new
        if (cfg is None) or ((isinstance(cfg, dict)) and (len(cfg) == 0)):
            cfg = default
        return cfg

    def set_item(self, itemname, value, replace=True):
        """Set a specific item in the configuration"""
        parts = itemname.split('.')
        cfg = self._cfg
        for i, part in enumerate(parts):
            if i + 1 < len(parts):
                item = cfg.get(part, None)
                if item is None:  # create hierarchy if not present
                    item = dict()
                    cfg[part] = item
                cfg = item
            else:
                if replace:
                    cfg[part] = value
                else:  # only set to new value if not existing (used for setting default values)
                    cfg[part] = cfg.get(part, value)
        self._is_changed = True

    def set_item_default(self, itemname, value):
        """Sets the default configuration for the specified item"""
        self.set_item(itemname, value, replace=False)

    def delete(self, itemname):
        """Deletes the specific item from the configuration (low level)"""
        del(self._cfg[itemname])
        self._is_changed = True

    def delete_item(self, itemname):
        """Deletes the specific item from the configuration"""
        parts = itemname.split('.')
        cfg = self._cfg
        for part in parts:
            cfg_previous = cfg
            cfg = cfg.get(part, dict())
        if (cfg is None) or (len(cfg) == 0):
            return False
        else:
            del(cfg_previous[part])
            self._is_changed = True
            return True
