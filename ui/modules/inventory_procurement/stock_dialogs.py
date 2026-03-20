from importlib import import_module as _import_module
import sys as _sys

_sys.modules[__name__] = _import_module("ui.modules.inventory_procurement.stock_control.stock_dialogs")
