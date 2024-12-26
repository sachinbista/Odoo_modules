from odoo import api, fields, models

GOALS_FOR = [
        ('opportunity_no', 'Opportunity Count'),
        ('won_no', 'Won Count'),
        ('won_amount', 'Won Amount'),
        ('loss_amount', 'Loss Amount'),
        ('avg_closing_date', 'Average Closing Date'),
        ('retail_sale_amount', 'Retail Sale Amount'),
        ('sold_amount', 'Sold Amount'),
        ('return_amount', 'Returned Amount'),
        ('gross_percentage', 'Gross Margin Percentage'),
        ('sold_item_no', 'Sold Item Count'),
        ('repair_sold_amount', 'Repair Sold Amount'),
        ('repair_gross_amount', 'Repair Gross Amount'),
        ('service_sold_amount', 'Service Sold Amount'),
        ('service_gross_amount', 'Service Gross Amount'),
        ('closing_ratio', 'Closing Ratio'),
        ('items_per_transaction', 'Items Per Transaction'),
        ('birthday_percentage', 'Birthday %'),
        ('email_address_percentage', 'Email Address %'),
        ('contact_card_completion', 'Contact Card Completion'),
    ]


class GoalDefinition(models.Model):

    _inherit = 'gamification.goal.definition'
    
    goal_for = fields.Selection(selection=GOALS_FOR, string='Goal Defined for')
    
    

class Goal(models.Model):

    _inherit = 'gamification.goal'

    goal_for = fields.Selection(string='Goal Defined for', related='definition_id.goal_for', store= True, readonly=True)
