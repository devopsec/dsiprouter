import sys, os
if sys.path[0] != '/etc/dsiprouter/gui':
    sys.path.insert(0, '/etc/dsiprouter/gui')

from flask import Blueprint, session,render_template, request
from modules.agents.api.routes import agents_api
from modules.agents.db.dsip_agent import Base, dSIPAgent

agents = agents_api

# Module Metadata
name = "agents"
publisher = "dSIPRouter"
menu_name = "Voice AI Agents"
menu_icon = "ti ti-user"
description = "dSIPRouter Agents Management Module"
version = "1.0.0"
dsip_min_version = "0.78"


def init_db(mapper,dbengine):

    Base.metadata.create_all(dbengine)
    #mapper.map_imperatively(dSIPNumber, dsip_number)


def init_module(app, csrf, settings):
    """Initialize the agents module by registering its blueprint."""
    app.register_blueprint(agents) 
    csrf.exempt(agents)

