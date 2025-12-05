import sys, os
if sys.path[0] != '/etc/dsiprouter/gui':
    sys.path.insert(0, '/etc/dsiprouter/gui')

from flask import Blueprint
from modules.numbers.db.dsip_number import dSIPNumber
from database import startSession, DummySession
from modules.api.api_functions import createApiResponse, showApiError, api_security
from shared import getRequestData, rowToDict
from sqlalchemy import or_
from werkzeug import exceptions as http_exceptions

numbers_api = Blueprint('numbers_api', __name__)
# export a `numbers` symbol for consistency with other modules' imports
numbers = numbers_api


@numbers_api.route('/api/v1/numbers', methods=['GET'])
@api_security
def get_numbers():
    """Get list of numbers. Supports query params: source, starts_with, contains, ends_with, status."""
    db = DummySession()
    try:
        db = startSession()

        source = None
        starts_with = None
        contains = None
        ends_with = None
        status = None

        # extract from query string
        payload = getRequestData()
        source = payload['source']
        starts_with = payload['starts_with']
        contains = payload['contains']
        ends_with = payload['ends_with']
        status = payload['status']

        q = db.query(dSIPNumber)

        if source:
            # support using source as either carrier or pool
            q = q.filter(or_(dSIPNumber.carrier == source, dSIPNumber.pool == source))

        if starts_with:
            q = q.filter(dSIPNumber.did.like(f"{starts_with}%"))
        if contains:
            q = q.filter(dSIPNumber.did.like(f"%{contains}%"))
        if ends_with:
            q = q.filter(dSIPNumber.did.like(f"%{ends_with}"))
        if status is not None and status != '':
            q = q.filter(dSIPNumber.status == status)

        results = q.all()
        data = [rowToDict(r) for r in results]

        return createApiResponse(msg='Numbers retrieved', data=data)

    except Exception as ex:
        db.rollback()
        db.flush()
        return showApiError(ex)
    finally:
        db.close()


@numbers_api.route('/api/v1/numbers', methods=['POST'])
@api_security
def create_number():
    db = DummySession()
    try:
        db = startSession()
        payload = getRequestData()
        did = payload.get('did')
        if not did:
            raise http_exceptions.BadRequest('did is required')

        number = dSIPNumber(
            did=did,
            status=payload.get('status'),
            carrier=payload.get('carrier'),
            pool=payload.get('pool'),
            assigned_length=payload.get('assigned_length'),
            assigned_reference_id=payload.get('assigned_reference_id'),
        )

        db.add(number)
        db.flush()
        db.commit()

        return createApiResponse(msg='Number created', data=[rowToDict(number)])
    except Exception as ex:
        db.rollback()
        db.flush()
        return showApiError(ex)
    finally:
        db.close()


@numbers_api.route('/api/v1/numbers/<int:number_id>', methods=['PUT'])
@api_security
def update_number(number_id):
    db = DummySession()
    try:
        db = startSession()
        payload = getRequestData()

        number = db.query(dSIPNumber).filter(dSIPNumber.id == number_id).first()
        if number is None:
            raise http_exceptions.NotFound('Number not found')

        # update fields
        for key in ('did', 'status', 'carrier', 'pool', 'assigned_length', 'assigned_reference_id'):
            if key in payload:
                setattr(number, key, payload.get(key))

        db.add(number)
        db.flush()
        db.commit()

        return createApiResponse(msg='Number updated', data=[rowToDict(number)])
    except Exception as ex:
        db.rollback()
        db.flush()
        return showApiError(ex)
    finally:
        db.close()


@numbers_api.route('/api/v1/numbers/<int:number_id>', methods=['DELETE'])
@api_security
def delete_number(number_id):
    db = DummySession()
    try:
        db = startSession()
        number = db.query(dSIPNumber).filter(dSIPNumber.id == number_id).first()
        if number is None:
            raise http_exceptions.NotFound('Number not found')

        db.delete(number)
        db.flush()
        db.commit()

        return createApiResponse(msg='Number deleted', data=[{'id': number_id}])
    except Exception as ex:
        db.rollback()
        db.flush()
        return showApiError(ex)
    finally:
        db.close()
