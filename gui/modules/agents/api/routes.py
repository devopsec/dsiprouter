import sys, os

import requests
if sys.path[0] != '/etc/dsiprouter/gui':
    sys.path.insert(0, '/etc/dsiprouter/gui')

from flask import Blueprint, jsonify, request
from database import startSession, DummySession
from modules.api.api_functions import createApiResponse, showApiError, api_security
from shared import getRequestData, rowToDict
from modules.agents.db.dsip_agent import dSIPAgent as dSIPAgent
from modules.agents.db.dsip_agent import dSIPAgentInstruction as dSIPAgentInstruction
from sqlalchemy import exc as sql_exceptions
from werkzeug import exceptions as http_exceptions
from flask import render_template
import settings

# Setup some reusable variables and functions for the module
# Set OPENAI_BASE_URL from settings or use default
OPENAI_BASE_URL = settings.OPENAI_BASE_URL if hasattr(settings, 'OPENAI_BASE_URL') else 'https://api.openai.com/v1'

agents_api = numbers_api = Blueprint('agents', __name__, template_folder='../templates', static_folder='../static', static_url_path='/agents/static')



def _map_payload_to_agent(payload):
    # Map incoming payload keys to dSIPAgent attributes
    mapped = {}
    mapped['name'] = payload.get('agent-name', payload.get('name', ''))
    mapped['type'] = payload.get('agent-type', payload.get('type', ''))
    mapped['project_id'] = payload.get('agent-project-id', payload.get('project_id', ''))
    mapped['greeting_message'] = payload.get('agent-greeting-message', payload.get('greeting_message', ''))
    mapped['instructions'] = payload.get('agent-instructions', payload.get('instructions', ''))
    mapped['instructions_id'] = payload.get('agent-instructions-id', payload.get('agent-instructions-id', payload.get('instructions_id', 0))) or 0
    mapped['guardrails'] = payload.get('agent-guardrails', payload.get('guardrails', ''))
    mapped['tools'] = payload.get('agent-tools', payload.get('tools', ''))
    mapped['callback_email'] = payload.get('agent-callback-email', payload.get('callback_email', ''))
    mapped['did_mappings'] = payload.get('agent-did-mapping', payload.get('did_mappings', ''))
    mapped['deployment_type'] = payload.get('agent-deployment-type', payload.get('deployment_type', ''))
    mapped['deployment_profile_id'] = payload.get('agent-deployment-profile-id', payload.get('deployment_profile_id', 0)) or 0
    return mapped


def _map_payload_to_instruction(payload):
    # Map incoming payload keys to dSIPAgentInstruction attributes
    mapped = {}
    mapped['name'] = payload.get('instruction-name', payload.get('name', ''))
    mapped['project_type'] = payload.get('instruction-project-type', payload.get('project_type', 'openai')) or 'openai'
    mapped['instructions'] = payload.get('instruction-text', payload.get('instructions', ''))
    return mapped


@agents_api.route('/gui/agents', methods=['GET'])
def get_agents_page():
    return render_template('agents.html')

@agents_api.route('/api/v1/agent', methods=['GET'])
@agents_api.route('/api/v1/agent/<int:agent_id>', methods=['GET'])
@api_security
def get_agent(agent_id=None):
    db = DummySession()
    try:
        db = startSession()
        if agent_id is None:
            # list all
            agents = db.query(dSIPAgent).all()
            data = [rowToDict(a) for a in agents]
            return createApiResponse(msg='Agents retrieved', data=data)
        else:
            agent = db.query(dSIPAgent).filter(dSIPAgent.id == agent_id).first()
            if agent is None:
                raise http_exceptions.NotFound('Agent not found')
            return createApiResponse(msg='Agent retrieved', data=[rowToDict(agent)])
    except Exception as ex:
        db.rollback()
        db.flush()
        return showApiError(ex)
    finally:
        db.close()


@agents_api.route('/api/v1/agent', methods=['POST'])
@api_security
def create_agent():
    db = DummySession()
    try:
        db = startSession()
        payload = getRequestData()
        mapped = _map_payload_to_agent(payload)

        agent = dSIPAgent(
            name=mapped['name'],
            type=mapped['type'],
            project_id=mapped['project_id'],
            greeting_message=mapped['greeting_message'],
            instructions=mapped['instructions'],
            instructions_id=int(mapped.get('instructions_id', 0)),
            guardrails=mapped.get('guardrails', ''),
            training_website=mapped.get('training_website', ''),
            tools=mapped.get('tools', ''),
            callback_email=mapped.get('callback_email', ''),
            did_mappings=mapped.get('did_mappings', ''),
            deployment_type=mapped.get('deployment_type', ''),
            deployment_profile_id=int(mapped.get('deployment_profile_id', 0)),
        )

        db.add(agent)
        db.flush()
        db.commit()

        return createApiResponse(msg='Agent created', data=[rowToDict(agent)])
    except Exception as ex:
        db.rollback()
        db.flush()
        return showApiError(ex)
    finally:
        db.close()


@agents_api.route('/api/v1/agent/<int:agent_id>', methods=['PUT'])
@api_security
def update_agent(agent_id):
    db = DummySession()
    try:
        db = startSession()
        payload = getRequestData()
        mapped = _map_payload_to_agent(payload)

        agent = db.query(dSIPAgent).filter(dSIPAgent.id == agent_id).first()
        if agent is None:
            raise http_exceptions.NotFound('Agent not found')

        # update fields
        for k, v in mapped.items():
            # map keys to attribute names on the model
            if hasattr(agent, k):
                setattr(agent, k, v)

        db.add(agent)
        db.flush()
        db.commit()

        return createApiResponse(msg='Agent updated', data=[rowToDict(agent)])
    except Exception as ex:
        db.rollback()
        db.flush()
        return showApiError(ex)
    finally:
        db.close()


@agents_api.route('/api/v1/agents/<int:agent_id>', methods=['DELETE'])
@api_security
def delete_agent(agent_id):
    db = DummySession()
    try:
        db = startSession()

        agent = db.query(dSIPAgent).filter(dSIPAgent.id == agent_id).first()
        if agent is None:
            raise http_exceptions.NotFound('Agent not found')

        db.delete(agent)
        db.flush()
        db.commit()

        return createApiResponse(msg='Agent deleted', data=[{'id': agent_id}])
    except Exception as ex:
        db.rollback()
        db.flush()
        return showApiError(ex)
    finally:
        db.close()


@agents_api.route('/api/agents/v1/instructions', methods=['GET'])
@agents_api.route('/api/agents/v1/instructions/<int:instruction_id>', methods=['GET'])
@api_security
def get_agent_instructions(instruction_id=None):
    db = DummySession()
    try:
        db = startSession()
        if instruction_id is None:
            instructions = db.query(dSIPAgentInstruction).all()
            data = [rowToDict(instruction) for instruction in instructions]
            return createApiResponse(msg='Instructions retrieved', data=data)

        instruction = db.query(dSIPAgentInstruction).filter(dSIPAgentInstruction.id == instruction_id).first()
        if instruction is None:
            raise http_exceptions.NotFound('Instruction not found')

        return createApiResponse(msg='Instruction retrieved', data=[rowToDict(instruction)])
    except Exception as ex:
        db.rollback()
        db.flush()
        return showApiError(ex)
    finally:
        db.close()


@agents_api.route('/api/agents/v1/instructions', methods=['POST'])
@api_security
def create_agent_instruction():
    db = DummySession()
    try:
        db = startSession()
        payload = getRequestData()
        mapped = _map_payload_to_instruction(payload)

        instruction = dSIPAgentInstruction(
            name=mapped['name'],
            project_type=mapped['project_type'],
            instructions=mapped['instructions'],
        )

        db.add(instruction)
        db.flush()
        db.commit()

        return createApiResponse(msg='Instruction created', data=[rowToDict(instruction)])
    except Exception as ex:
        db.rollback()
        db.flush()
        return showApiError(ex)
    finally:
        db.close()


@agents_api.route('/api/agents/v1/instructions/<int:instruction_id>', methods=['PUT'])
@api_security
def update_agent_instruction(instruction_id):
    db = DummySession()
    try:
        db = startSession()
        payload = getRequestData()
        mapped = _map_payload_to_instruction(payload)

        instruction = db.query(dSIPAgentInstruction).filter(dSIPAgentInstruction.id == instruction_id).first()
        if instruction is None:
            raise http_exceptions.NotFound('Instruction not found')

        for k, v in mapped.items():
            if hasattr(instruction, k):
                setattr(instruction, k, v)

        db.add(instruction)
        db.flush()
        db.commit()

        return createApiResponse(msg='Instruction updated', data=[rowToDict(instruction)])
    except Exception as ex:
        db.rollback()
        db.flush()
        return showApiError(ex)
    finally:
        db.close()


@agents_api.route('/api/agents/v1/instructions/<int:instruction_id>', methods=['DELETE'])
@api_security
def delete_agent_instruction(instruction_id):
    db = DummySession()
    try:
        db = startSession()

        instruction = db.query(dSIPAgentInstruction).filter(dSIPAgentInstruction.id == instruction_id).first()
        if instruction is None:
            raise http_exceptions.NotFound('Instruction not found')

        db.delete(instruction)
        db.flush()
        db.commit()

        return createApiResponse(msg='Instruction deleted', data=[{'id': instruction_id}])
    except Exception as ex:
        db.rollback()
        db.flush()
        return showApiError(ex)
    finally:
        db.close()


@agents_api.route('/api/agents/v1/projects/<string:provider>', methods=['GET'])
@api_security
def get_projects_by_provider(provider):
    db = DummySession()

    if provider.lower() != 'openai':
        return showApiError(f'Provider {provider} not supported', code=400) 
    try:
        headers = {'Authorization': f'Bearer {settings.OPENAI_API_KEY}'
                   , 'Content-Type': 'application/json'}
       
        print(headers)
        r = requests.get(f'{OPENAI_BASE_URL}/organization/projects', headers=headers)
        if r.status_code != 200:
            raise http_exceptions.InternalServerError(f'Failed to retrieve projects from provider: {provider}. \
                 HTTP Return Status Code {r.status_code}: {r.reason}')
        projects = r.json().get('data', [])
        return createApiResponse(msg='Projects retrieved', data=projects)
    except Exception as ex:
        db.rollback()
        db.flush()
        return showApiError(ex)
    finally:
        db.close()

