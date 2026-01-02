import sys, os
if sys.path[0] != '/etc/dsiprouter/gui':
    sys.path.insert(0, '/etc/dsiprouter/gui')

from flask import Blueprint, session,render_template, request
from modules.numbers.api.routes import numbers_api

numbers = numbers_api

# Module Metadata
module_name = "numbers"
module_publisher = "dSIPRouter"
module_menu_name = "Numbers"
module_description = "dSIPRouter Numbers Management Module"
module_version = "1.0.0"

def init_module(app, csrf, settings):
    """Initialize the numbers module by registering its blueprint."""
    app.register_blueprint(numbers) 
    csrf.exempt(numbers)

