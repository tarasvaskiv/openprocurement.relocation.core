# -*- coding: utf-8 -*-
from logging import getLogger
from pkg_resources import get_distribution, iter_entry_points

PKG = get_distribution(__package__)

LOGGER = getLogger(PKG.project_name)


def main(config):
    from openprocurement.relocation.core.utils import (transfer_from_data, extract_transfer)
    LOGGER.info('Init relocation core plugin.')
    config.add_request_method(extract_transfer, 'transfer', reify=True)
    config.add_request_method(transfer_from_data)

    config.scan("openprocurement.relocation.core.views")

    plugins = config.registry.settings.get('plugins') and config.registry.settings['plugins'].split(',')
    for entry_point in iter_entry_points('openprocurement.relocation.core.plugins'):
        if not plugins or entry_point.name in plugins:
            plugin = entry_point.load()
            plugin(config)
