# -*- encoding: utf-8 -*-
##############################################################################
#    
#    Odoo, Open Source Management Solution
#
#    Author: Andrius Laukavičius. Copyright: Andrius Laukavičius
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

from openerp import models, fields
from openerp import api
from datetime import datetime, timedelta
from openerp.exceptions import Warning
from openerp.tools.translate import _

class crm_lead_stage_log(models.Model):
	_name = 'crm.lead.stage_log'
	_description = 'Lead/Opp. Stages Log'

	lead_id = fields.Many2one('crm.lead', 'Lead/Opportunity')
	user_id = fields.Many2one('res.users', 'Responsible')
	stage_id = fields.Many2one('crm.case.stage', 'Stage')
 	prev_stage_id = fields.Many2one('crm.case.stage', 'Previous Stage')
	section_id = fields.Many2one('crm.case.section', 'Sales Team')
	lead_type = fields.Selection([('lead', 'Lead'), ('opportunity', 'Opportunity')], 'Type')

class crm_lead(models.Model):
	_inherit = 'crm.lead'

	stage_deadline = fields.Datetime('Stage Deadline', compute="_compute_stage_deadline")
	hide_stage_btn = fields.Boolean('Hide Next Stage Button')

	@api.multi
	@api.returns('crm.case.section.stage_config')
	def get_stage_config(self):
		stage_config = self.env['crm.case.section.stage_config'].search(
			[('section_id', '=', self.section_id.id), ('stage_id', '=', self.stage_id.id)])
		while stage_config:
			return stage_config	

	@api.multi
	@api.returns('crm.lead.stage_log')
	def get_stage_log(self):
		stage_log = self.env['crm.lead.stage_log'].search(
			[('lead_id', '=', self.id), ('stage_id', '=', self.stage_id.id)])
		while stage_log:
			return stage_log				

	@api.one
	def next_stage(self):
		stage_config = self.get_stage_config()
		if stage_config:
			if stage_config.next_stage_id: 
				if stage_config.next_stage_id:
					self.stage_id = stage_config.next_stage_id.id			
					if self.stage_id.probability == 100.0 or self.stage_id.probability == 0.0:
						self.hide_stage_btn = True
					stage_config_next = self.get_stage_config()
					if 	stage_config_next and stage_config_next.user_id:
						self.user_id = stage_config_next.user_id.id							
					log_vals = {'lead_id': self.id, 'user_id': self.user_id.id, 
						'stage_id': self.stage_id.id, 'prev_stage_id': stage_config.stage_id.id,
						'section_id': self.section_id.id,
						'lead_type': self.type,
					}
					self.env['crm.lead.stage_log'].create(log_vals)
				else:
					raise Warning(_('"%s" Stage is not Set for %s Team!' % (stage_config.next_stage_id.name, self.section_id.name)))

	@api.one
	def reset_stage(self):
		if self.section_id.default_stage:
			self.stage_id = self.section_id.default_stage.id					
		else:
			raise Warning(_('There is no default Stage defined!'))

					

	@api.model
	def create(self, vals):
		"""
		Logs init stage on creation.
		"""
		lead = super(crm_lead, self).create(vals)			
		log_vals = {'lead_id': lead.id, 'user_id': lead.user_id.id, 
			'stage_id': lead.stage_id.id, 'lead_type': lead.type, 'section_id': self.section_id.id}
		self.env['crm.lead.stage_log'].create(log_vals)
		return lead
	
	def _convert_opportunity_data(self,cr , uid, lead, customer, section_id=False, context=None):
		"""
		Logs stage information on conversion
		"""
		vals = super(crm_lead, self)._convert_opportunity_data(cr, uid, lead, customer, section_id=False, context=None)
		log_vals = {
			'lead_id': lead.id, 'user_id': lead.user_id.id, 
			'stage_id': lead.stage_id.id, 'section_id': lead.section_id.id,
			'lead_type': 'opportunity',
		}
		self.pool.get('crm.lead.stage_log').create(cr, uid, log_vals, context=context)
		return vals


	@api.one
	def _compute_stage_deadline(self):
		self.stage_deadline = None		
		stage_config = self.get_stage_config()
		if stage_config:
			stage_logs = self.get_stage_log()
			if stage_logs:
				stage_log = stage_logs[-1]				
				create_date = datetime.strptime(stage_log.create_date, "%Y-%m-%d %H:%M:%S")				
				self.stage_deadline = create_date + timedelta(days=stage_config.days_for_stage)