# -*- coding: utf-8 -*-
from odoo import http

# class ServiceStation(http.Controller):
#     @http.route('/service_station/service_station/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/service_station/service_station/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('service_station.listing', {
#             'root': '/service_station/service_station',
#             'objects': http.request.env['service_station.service_station'].search([]),
#         })

#     @http.route('/service_station/service_station/objects/<model("service_station.service_station"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('service_station.object', {
#             'object': obj
#         })