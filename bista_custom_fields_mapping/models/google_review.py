# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
#############################################################################
from odoo import fields,models,api
import urllib

# import os, httplib2, argparse
# import requests
import json
# from oauth2client.client import flow_from_clientsecrets
# from oauth2client.file import Storage
# from oauth2client import tools
# from googleapiclient.discovery import build
# from apiclient import errors
# from googleapiclient import sample_tools

import logging

_logger = logging.getLogger(__name__)

class GoogleReveiw(models.Model):
    _name = 'google.review'
    _description = 'Google Website Reviews'

    name = fields.Char(string='Person Name',required=True)
    rate = fields.Float(string='Rate',required=True)
    review = fields.Text(string='Review')
    seq = fields.Integer(string='Sequence')
    active = fields.Boolean(string='Active' ,default=True)
    period = fields.Char(string='Period')

    # @api.multi
    def fetch_reviews(self):

        # self.test_google()
        url = "https://maps.googleapis.com/maps/api/place/details/json?placeid=ChIJp-1bDwfHJIgRaCzyHbeF7P4&key=AIzaSyB9R9UkbdaJK4w0ffqGJs9gfg_0-HPnXnU"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read())
        try:
            for d in data.get('result').get('reviews'):
                reviews = self.env['google.review'].search_count([('name','=',d.get('author_name')), ('review','=',d.get('text'))])
                if reviews < 1:
                    # if d.get('rating') > 3 :
                    vals = {
                            'name' :d.get('author_name'),
                            'rate' : d.get('rating'),
                            'review' : d.get('text'),
                            'period' : d.get('relative_time_description'),
                    }
                    self.env['google.review'].create(vals)
        except:
            _logger.error('API Key Expired')


