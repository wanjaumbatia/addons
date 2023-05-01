import ast
import functools
import json
import logging
import re

from odoo import http
from odoo.addons.restful.common import extract_arguments, invalid_response, valid_response
from odoo.exceptions import AccessError
from odoo.http import request

_logger = logging.getLogger(__name__)


def validate_token(func):
    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        """."""
        access_token = request.httprequest.headers.get("access_token")
        if not access_token:
            return invalid_response("access_token_not_found", "missing access token in request header", 401)
        access_token_data = (
            request.env["api.access_token"].sudo().search([("token", "=", access_token)], order="id DESC", limit=1)
        )

        if access_token_data.find_one_or_create_token(user_id=access_token_data.user_id.id) != access_token:
            return invalid_response("access_token", "token seems to have expired or invalid", 401)

        request.session.uid = access_token_data.user_id.id
        request.update_env(user=request.session.uid)
        return func(self, *args, **kwargs)

    return wrap


_routes = ["/api/<model>", "/api/<model>/<id>", "/api/<model>/<id>/<action>"]


class APIController(http.Controller):
    """."""

    def __init__(self):
        self._model = "ir.model"

    @validate_token
    @http.route("/api/contacts", type="http", auth="public", methods=["GET"], csrf=False,)
    def get(self, **payload):
        try:
            data =  http.request.env['res.partner'].search_read()
            print(request.uid)
            return valid_response(data)
        except AccessError as e:
            return invalid_response("Access error", "Error: %s" % e.name)

    @validate_token
    @http.route("/api/contacts/<id>", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def getOne(self, id=None, **payload):
        try:
            domain = [("id", "=", int(id))]
            data = http.request.env['res.partner'].search_read(domain=domain)
            if data:
                return valid_response(data[0])
            else:
                return None
        except AccessError as e:
            return invalid_response("Access error", "Error: %s" % e.name)

