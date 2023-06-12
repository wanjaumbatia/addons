import werkzeug.wrappers
import ast
import functools
import json
import logging
import re
from datetime import datetime, timedelta
from odoo import http, _
from odoo.addons.restful.common import invalid_response, valid_response
from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.http import request
from dateutil import parser
from pytz import timezone

_logger = logging.getLogger(__name__)


class MainController(http.Controller):

    # CREATE CONTACT
    @http.route("/api/create_contact", methods=["POST"], type="http", cors="*", auth="public", csrf=False)
    def create_contact(self, **post):
        payload = request.httprequest.data.decode()
        payload = json.loads(payload)

        contact_check = request.env['res.partner'].search_count([("email", "=", payload['email'])], limit=1)

        if contact_check > 0:
            return werkzeug.wrappers.Response(
                status=400,
                content_type="application/json; charset=utf-8",
                headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
                response=json.dumps(
                    {
                        "message": "Contact already exists"
                    }
                ),
            )

        partner = request.env['res.partner'].sudo().create(
            {
                'name': payload['name'],
                'company_type': 'person',
                'country_id': request.env['res.country'].search([('code', '=', 'KE')], limit=1).id,
                'email': payload['email'],
                'phone': payload['phone'],
                'mobile': payload['phone'],
                'function': 'Customer',
                'comment': 'Customer Contact',
                'category_id': [
                    (6, 0, [request.env['res.partner.category'].sudo().search([('name', '=', 'Customers')],
                                                                              limit=1).id])]
            }
        )

        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(
                {
                    "contact": partner.id
                }
            ),
        )

    @http.route("/api/personnel", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def fetch_personnel(self, **kw):
        domain = []
        if kw.get('domain', ''):
            domain = kw.get('domain', '')
            domain = ast.literal_eval(domain)

        fields = []
        if kw.get('fields', ''):
            fields = kw.get('fields', '')
            fields = fields.split(',')

        data = request.env['hr.employee'].sudo().search_read(
            domain=[('is_nurse', '=', True)], fields=fields
        )
        return valid_response(data)

    @http.route("/api/categories", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def fetch_categories(self, **kw):
        data = request.env['afyaplug.category'].sudo().search_read(fields=['id','name','enabled'])
        return valid_response(data)

    @http.route("/api/services", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def fetch_services(self, **kw):
        data = request.env['product.template'].sudo().search_read(fields=[
            'name', 'category_id', 'detailed_type', 'standard_price'
        ])
        return valid_response(data)
    @http.route("/api/nurses/<id>", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def getNurse(self, id=None, **kw):
        domain = [("id", "=", int(id))]
        fields = []
        if kw.get('fields', ''):
            fields = kw.get('fields', '')
            fields = fields.split(',')

        data = request.env['hr.employee'].sudo().search_read(
            domain=domain, fields=fields
        )
        return valid_response(data[0])

    @http.route("/api/appointment", type="http", auth="public", methods=["POST"], csrf=False, cors="*")
    def book_appointment(self, **payload):
        payload = request.httprequest.data.decode()
        payload = json.loads(payload)

        nurse_list = request.env['hr.employee'].sudo().search(
            domain=[('id', '=', payload['nurse_id'])]
        )
        nurse = nurse_list[0]

        product_list = request.env['product.product'].sudo().search(
            domain=[('id', '=', payload['product_id'])]
        )
        user = request.env['res.users'].sudo().search(
            domain=[('id', '=', request.uid)]
        )

        product = product_list[0]
        start_datetime_str = payload['start_datetime']
        stop_datetime_str = payload['stop_datetime']

        start_datetime = datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M:%S')
        stop_datetime = datetime.strptime(stop_datetime_str, '%Y-%m-%d %H:%M:%S')

        appointment = request.env['afyaplug.appointment'].sudo().create({
            'contact_id': user.partner_id.id,
            'nurse_id': nurse.id,
            'product_id': product.id,
            'street': payload['street'],
            'street2': payload['street2'],
            'landmark': payload['landmark'],
            'town': payload['town'],
            'county': payload['county'],
            'appointment_date': start_datetime,
            'appointment_time': stop_datetime
        })

        # Create a new event for the employee in the calendar
        event = request.env['calendar.event'].sudo().create({
            'start': start_datetime,
            'stop': stop_datetime,
            'name': appointment.reference + " - " + user.partner_id.name,
            'partner_ids': [(4, nurse.user_id.partner_id.id), (4, user.partner_id.id)]
        })

        return valid_response(event.id)

    @http.route("/api/schedule/<id>", type="http", auth="public", methods=["POST"], csrf=False, cors="*")
    def nurses_schedule(self, id=None, **payload):
        nurse = request.env['hr.employee'].sudo().search([('id', '=', id)])
        payload = request.httprequest.data.decode()
        payload = json.loads(payload)

        events = request.env['calendar.event'].sudo().search_read([])
        print(events)
        appointment_date = payload['date']
        return valid_response(events[0]['partner_ids'])

    @http.route('/employee/<int:employee_id>/free_slots', auth='public', type='http', methods=['GET'], csrf=False)
    def get_employee_free_slots(self, employee_id, start_date=None, end_date=None, **kwargs):
        try:
            employee = request.env['hr.employee'].sudo().search([('id', '=', employee_id)])
        except:
            raise UserError(_('Invalid employee ID'))


        partner_id = employee.read(['user_partner_id'])[0]['user_partner_id'][0]

        calendar = request.env['calendar.event'].sudo().search([
            ('start', '>=', datetime.now()),
            ('partner_ids', 'in', [partner_id]),
        ], order='start asc')
        print(calendar)
        if calendar:
            return valid_response(calendar.read())
        else:
            return valid_response({'message': 'No events found'})



