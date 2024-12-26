from odoo import models, fields, api, _
from tomlkit import string


class TransitWizard(models.TransientModel):
    _name = 'transit.wizard'
    _description = 'Transit Wizard'

    transit_date = fields.Date(string="In-transit Date")
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order')
    transit_line_ids = fields.One2many('transit.line.wizard', 'transit_id', string='Transit Lines')

    def action_transit(self):
        journal_id = self.env['account.journal'].sudo().search([
            ('type','=','general'),('code', '=', 'STJ'),
            ('company_id','=',self.purchase_id.company_id.id)],limit=1)
        self.create_journal_entry(self.purchase_id,journal_id)
        self.create_landed_cost_journal_entry(self.purchase_id,journal_id)

    def create_journal_entry(self, purchase_id,journal_id):
        # Initialize line_ids for the journal entry lines
        line_ids = []

        # Set the debit account from the company in-transit account
        debit_account_id = purchase_id.company_id.in_transit_account_id
        if not debit_account_id:
            raise ValueError("No in-transit account defined in the company settings.")

        # Calculate total debit amount
        total_debit = 0.0

        # Loop through each line in the move
        lines = self.transit_line_ids.filtered(lambda line: not line.is_transit and not line.is_landed_cost)
        for line in lines:
            # Credit account from product category income account
            credit_account_id = line.product_id.categ_id.property_stock_account_input_categ_id
            if not credit_account_id:
                raise ValueError(
                    f"No income account defined for product category {line.product_id.categ_id.name}.")

            line.purchase_line_id.is_transit = True
            # Update the debit amount
            total_debit += line.price

            # Add a credit line for each move line
            line_ids.append({
                'account_id': credit_account_id.id,
                'name': purchase_id.name,
                'partner_id': purchase_id.partner_id.id,
                'debit': 0.0,
                'credit': line.price,
            })

        if total_debit > 0.0:
            # Add a single debit line for the total debit amount
            line_ids.insert(0, {
                'account_id': debit_account_id.id,
                'name': purchase_id.name,
                'partner_id': purchase_id.partner_id.id,
                'debit': total_debit,
                'credit': 0.0,
            })

        if line_ids:

            # Create the journal entry
            journal_entry = self.env['account.move'].create({
                'move_type': 'entry',  # Set to 'entry' for a manual journal entry
                'date': self.transit_date,
                'partner_id': purchase_id.partner_id.id,
                'ref': purchase_id.name,
                'transit_id': purchase_id.id,
                'journal_id': journal_id.id,  # Use journal from move if available
                'line_ids': [(0, 0, line) for line in line_ids],
            })

            # Post the journal entry to validate it
            journal_entry.action_post()

    def create_landed_cost_journal_entry(self,purchase_id, journal_id):
        line_ids = []
        debit_account_id = purchase_id.company_id.in_transit_account_id
        total_debit = 0.0
        lines = self.transit_line_ids.filtered(lambda x: x.is_landed_cost)
        for line in lines:
            credit_account_id = line.product_id.categ_id.property_stock_account_input_categ_id
            if not credit_account_id:
                raise ValueError(
                    f"No stock input acccount defined for product category {line.product_id.categ_id.name}.")

            # Update the debit amount
            total_debit += line.price

            # Add a credit line for each move line
            line_ids.append({
                'account_id': credit_account_id.id,
                'name': purchase_id.name,
                'partner_id': purchase_id.partner_id.id,
                'product_id': line.product_id.id,
                'debit': 0.0,
                'credit': line.price,
            })
        if total_debit > 0.0:
            line_ids.insert(0, {
                'account_id': debit_account_id.id,
                'name': purchase_id.name,
                'partner_id': purchase_id.partner_id.id,
                'debit': total_debit,
                'credit': 0.0,
            })
        if line_ids:
            # Create the journal entry
            journal_entry = self.env['account.move'].create({
                'move_type': 'entry',  # Set to 'entry' for a manual journal entry
                'date': self.transit_date,
                'partner_id': purchase_id.partner_id.id,
                'ref': purchase_id.name,
                'transit_id': purchase_id.id,
                'journal_id': journal_id.id,  # Use journal from move if available
                'line_ids': [(0, 0, line) for line in line_ids],
            })

        # Post the journal entry to validate it
            journal_entry.action_post()


class TransitLineWizard(models.TransientModel):
    _name = 'transit.line.wizard'
    _description = 'Transit Line Wizard'

    product_id = fields.Many2one('product.product', string='Product')
    price = fields.Float(string='Price')
    transit_id = fields.Many2one('transit.wizard', string='Transit Wizard')
    is_transit = fields.Boolean(string="In-Transit Created")
    is_landed_cost = fields.Boolean(string="Is Landed Cost")
    purchase_line_id = fields.Many2one("purchase.order.line",string="purchase line")

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id.landed_cost_ok:
            self.is_landed_cost = True
