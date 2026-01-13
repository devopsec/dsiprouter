import sys, os
if sys.path[0] != '/etc/dsiprouter/gui':
    sys.path.insert(0, '/etc/dsiprouter/gui')

from flask import Blueprint, session,render_template, request
from modules.numbers.api.routes import numbers_api

numbers = numbers_api

# Module Metadata
name = "numbers"
publisher = "dSIPRouter"
menu_name = "Numbers"
menu_icon = "glyphicon glyphicon-phone-alt"
description = "dSIPRouter Numbers Management Module"
version = "1.0.0"
dsip_min_version = "0.78"

def init_module(app, csrf, settings):
    """Initialize the numbers module by registering its blueprint."""
    app.register_blueprint(numbers) 
    csrf.exempt(numbers)

