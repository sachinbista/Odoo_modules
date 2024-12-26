from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    payment_difference_handling = fields.Selection(
        selection_add=[
            ("reconcile_multi_deduct", "Mark invoice as fully paid (multi deduct)")
        ],
        ondelete={"reconcile_multi_deduct": "cascade"},
    )
    deduct_residual = fields.Monetary(
        string="Remainings", compute="_compute_deduct_residual"
    )
    deduction_ids = fields.One2many(
        comodel_name="account.payment.deduction",
        inverse_name="payment_id",
        string="Deductions",
        copy=False,
        help="Sum of deduction amount(s) must equal to the payment difference",
    )
    writeoff_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Analytic Account",
        index=True,
    )
    # writeoff_analytic_tag_ids = fields.Many2many(
    #     comodel_name="account.analytic.tag",
    #     string="Analytic Tags",
    # )
    deduct_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        compute="_compute_default_analytic",
    )
    deduct_analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        compute="_compute_default_analytic",
    )
    check_number = fields.Char(string="Check Number")

    def _compute_group_payment(self):
        """"Override to process group payment."""
        res = super(AccountPaymentRegister, self)._compute_group_payment()
        for wizard in self:
            if wizard.can_edit_wizard:
                batches = wizard._get_batches()
                wizard.group_payment = True
            else:
                wizard.group_payment = False
        return res

    @api.depends("payment_difference", "deduction_ids")
    def _compute_default_analytic(self):
        active_ids = self.env.context.get("active_ids")
        moves = self.env["account.move"].browse(active_ids)
        move_lines = moves.mapped("line_ids")
        # analytic_account = move_lines.mapped("analytic_account_id")
        # analytic_tag = move_lines.mapped("analytic_tag_ids")
        taxes_account = (
            self.env["account.tax.repartition.line"]
            .search([("account_id", "!=", False)])
            .mapped("account_id")
        )
        moves_without_tax = move_lines.filtered(
            lambda l: l.account_id.account_type not in ('asset_receivable', 'liability_payable')
            and l.account_id.id not in taxes_account.ids
        )
        # default_tag = (
        #     all(line.analytic_tag_ids == analytic_tag for line in moves_without_tax)
        #     and analytic_tag
        #     or False
        # )
        for rec in self:
        #     rec.deduct_analytic_account_id = (
        #         len(analytic_account) == 1 and analytic_account.id or False
        #     )
        #     rec.deduct_analytic_tag_ids = default_tag
            rec.deduct_analytic_account_id = False
            rec.deduct_analytic_tag_ids = []

    def _update_vals_deduction(self, moves):
        move_lines = moves.mapped("line_ids")
        # analytic_account = move_lines.mapped("analytic_account_id")
        # analytic_tag = move_lines.mapped("analytic_tag_ids")
        taxes_account = (
            self.env["account.tax.repartition.line"]
            .search([("account_id", "!=", False)])
            .mapped("account_id")
        )
        # moves_without_tax = move_lines.filtered(
        #     lambda l: l.account_id.user_type_id.type not in ("payable", "receivable")
        #     and l.account_id.id not in taxes_account.ids
        # )
        # default_tag = (
        #     all(line.analytic_tag_ids == analytic_tag for line in moves_without_tax)
        #     and analytic_tag
        #     or False
        # )
        # self.writeoff_analytic_account_id = (
        #     len(analytic_account) == 1 and analytic_account.id or False
        # )
        # self.writeoff_analytic_tag_ids = default_tag

    @api.onchange("payment_difference", "payment_difference_handling")
    def _onchange_default_deduction(self):
        if self.payment_difference_handling == "reconcile":
            active_ids = self.env.context.get("active_ids", [])
            moves = self.env["account.move"].browse(active_ids)
            self._update_vals_deduction(moves)

    def action_create_payments(self):
        if self.payment_difference_handling == "reconcile_multi_deduct":
            self = self.with_context(
                skip_account_move_synchronization=True,
                dont_redirect_to_payments=True,
            )
        return super().action_create_payments()

    # @api.constrains("deduction_ids", "payment_difference_handling")
    # def _check_deduction_amount(self):
    #     prec_digits = self.env.user.company_id.currency_id.decimal_places
    #     for rec in self:
    #         if rec.payment_difference_handling == "reconcile_multi_deduct":
    #             if (
    #                 float_compare(
    #                     rec.payment_difference,
    #                     sum(rec.deduction_ids.mapped("amount")),
    #                     precision_digits=prec_digits,
    #                 )
    #                 != 0
    #             ):
    #                 raise UserError(
    #                     _("The total deduction should be %s") % rec.payment_difference
    #                 )

    @api.depends("payment_difference", "deduction_ids")
    def _compute_deduct_residual(self):
        for rec in self:
            rec.deduct_residual = rec.payment_difference - sum(
                rec.deduction_ids.mapped("amount_currency")
            )

    def _create_payment_vals_from_wizard(self, first_batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(first_batch_result)
        # payment difference
        if (
            not self.currency_id.is_zero(self.payment_difference)
            and self.payment_difference_handling == "reconcile"
        ):
            pass
            # payment_vals["write_off_line_vals"][
            #     "analytic_account_id"
            # ] = self.writeoff_analytic_account_id.id


            # payment_vals["write_off_line_vals"]["analytic_tag_ids"] = [
            #     (6, 0, self.writeoff_analytic_tag_ids.ids)
            # ]
        # multi deduction
        elif (
            self.payment_difference
            and self.payment_difference_handling == "reconcile_multi_deduct"
        ):
            payment_vals["write_off_line_vals"] = [
                self._prepare_deduct_move_line(deduct)
                for deduct in self.deduction_ids.filtered(lambda l: not l.open)
            ]
            payment_vals["is_multi_deduction"] = True
        payment_vals["check_number"] = self.check_number
        return payment_vals

    def _prepare_deduct_move_line(self, deduct):
        return {
            "name": deduct.name,
            "amount_currency": deduct.amount_currency,
            "balance": deduct.amount_currency,
            "account_id": deduct.account_id.id,
            # "analytic_account_id": deduct.analytic_account_id
            # and deduct.analytic_account_id.id
            # or False,
            # "analytic_tag_ids": deduct.analytic_tag_ids
            # and [(6, 0, deduct.analytic_tag_ids.ids)]
            # or False,
        }

    def _create_payments(self):
        payments = super(AccountPaymentRegister, self)._create_payments()
        if self._context.get('all_invoice_run'):
            for payment in payments:
                moves = self.line_ids.mapped('move_id').filtered(lambda m: m.commercial_partner_id.id == payment.partner_id.id)

                payment.write({'linked_bill_ids': [(6,0, moves.ids)]})
        return payments
