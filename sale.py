# This file is part of sale_pos module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal
from datetime import datetime
from trytond.model import ModelView, fields
from trytond.pool import PoolMeta, Pool
from trytond.transaction import Transaction
from trytond.pyson import Bool, Eval, Or
from trytond.wizard import (Wizard, StateView, StateAction, StateTransition,
    Button)
from trytond.config import config

__all__ = ['Sale', 'SaleLine']
__metaclass__ = PoolMeta

class Sale:
    __name__ = 'sale.sale'

    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()

        cls.sale_discount.states['readonly'] |= Eval('invoice_state') != 'none'

class SaleLine:
    __name__ = 'sale.line'

    aplicar_desglose = fields.Boolean('Aplicar con desglose')
    descuento_desglose = fields.Numeric('Descuento con desglose', states={
            'invisible': ~Eval('aplicar_desglose', True)})

    @classmethod
    def __setup__(cls):
        super(SaleLine, cls).__setup__()
        cls.discount.states['invisible'] |= Eval ('aplicar_desglose', True)
        cls.unit_price.digits = (16, 6)
        cls.unit_price_w_tax.digits = (16, 4)
        cls.amount_w_tax.digits = (16, 4)
        cls.descuento_desglose.digits = (16, 4)
        if 'descuento_desglose' not in cls.unit_price_w_tax.on_change_with:
            cls.unit_price_w_tax.on_change_with.add('descuento_desglose')
        if 'descuento_desglose' not in cls.amount_w_tax.on_change_with:
            cls.amount_w_tax.on_change_with.add('descuento_desglose')
        if 'descuento_desglose' not in cls.amount.on_change_with:
            cls.amount.on_change_with.add('descuento_desglose')
        cls.gross_unit_price.states['readonly'] = Eval('active', True)

    def update_prices(self):
        unit_price = None
        descuento = Decimal(0.0)
        gross_unit_price = gross_unit_price_wo_round = self.gross_unit_price
        sale_discount = Transaction().context.get('sale_discount')
        producto = self.product

        if producto:
            precio_costo = self.product.cost_price
        else:
            precio_costo = None
        origin = str(self)
        def in_group():
            pool = Pool()
            ModelData = pool.get('ir.model.data')
            User = pool.get('res.user')
            Group = pool.get('res.group')
            group = Group(ModelData.get_id('nodux_sale_pos_discount',
                        'group_cost_price_force_assignment'))
            transaction = Transaction()
            user_id = transaction.user
            if user_id == 0:
                user_id = transaction.context.get('user', user_id)
            if user_id == 0:
                return True
            user = User(user_id)
            return origin and group in user.groups

        if sale_discount == None:
            if self.sale and hasattr(self.sale, 'sale_discount'):
                sale_discount = self.sale.sale_discount or Decimal(0)
            else:
                sale_discount = Decimal(0)
        """
        if sale_discount:
            total = self.sale.total_amount
            value = total - (sale_discount*100)
            sale_discount = ((value * 100) / total)/100
        """
        if self.gross_unit_price is not None and (self.discount is not None
                or sale_discount is not None or self.descuento_desglose is not None):
            unit_price = self.gross_unit_price

            if self.discount and self.descuento_desglose:
                if self.quantity:
                    taxes = self.taxes
                    desglose = self.descuento_desglose
                    for t in taxes:
                        porcentaje = 1 + t.rate
                        unit_price = (desglose / porcentaje)

                    d = (unit_price/self.gross_unit_price)/100
                    dscto = 1- d
                    descuento = self.discount + d
                else:
                    descuento_inicial = 1 - (self.unit_price/self.gross_unit_price)
                    descuento = descuento_inicial + self.discount

                    desglose = self.descuento_desglose
                    taxes = self.taxes
                    if self.discount > 1:
                        e_d = str(self.discount * 100)
                        self.raise_user_error('No se puede aplicar un descuento de %s', e_d)

                    unit_price *= (1 - (descuento))

                    for t in taxes:
                        porcentaje = 1 + t.rate
                        unit = (desglose / porcentaje)

                    d = ((unit*100)/self.gross_unit_price)/100
                    dscto = 1- d


            elif self.discount:
                if self.discount > 1:
                    e_d = str(self.discount * 100)
                    self.raise_user_error('No se puede aplicar un descuento de %s', e_d)
                unit_price *= (1 - self.discount)

            elif self.descuento_desglose:
                taxes = self.taxes
                desglose = self.descuento_desglose
                if self.quantity:
                    for t in taxes:
                        porcentaje = 1 + t.rate
                        unit_price = (desglose / porcentaje)

                if self.gross_unit_price > Decimal(0.0):
                    d = ((unit_price*100)/self.gross_unit_price)/100
                    dscto = 1- d
                else:
                    d = ((unit_price*100)/unit_price)/100
                    dscto = 1- d

            if self.discount and sale_discount:
                discount = (self.discount + sale_discount
                    - self.discount * sale_discount)
                if discount != 1:
                    gross_unit_price_wo_round = unit_price / (1 - discount)

            elif self.discount and self.descuento_desglose:
                discount = (self.discount + d)
                if descuento != 1:
                    gross_unit_price_wo_round = self.gross_unit_price

            elif self.discount and self.discount != 1:
                gross_unit_price_wo_round = unit_price / (1 - self.discount)
            elif sale_discount and sale_discount != 1:
                gross_unit_price_wo_round = unit_price / (1 - sale_discount)
            elif self.descuento_desglose and self.descuento_desglose != 0:
                gross_unit_price_wo_round = unit_price / (1 - dscto)

            digits = self.__class__.unit_price.digits[1]
            unit_price = unit_price
            digits = self.__class__.gross_unit_price.digits[1]
            gross_unit_price = gross_unit_price_wo_round.quantize(
                Decimal(str(10.0 ** -digits)))

        return {
            'gross_unit_price': gross_unit_price,
            'gross_unit_price_wo_round': gross_unit_price_wo_round,
            'unit_price': unit_price,
            }

    @fields.depends('gross_unit_price', 'discount',
        '_parent_sale.sale_discount', 'descuento_desglose', 'product')
    def on_change_gross_unit_price(self):
        return self.update_prices()

    @staticmethod
    def default_descuento_desglose():
        return Decimal(0)

    @fields.depends('gross_unit_price', 'discount', 'unit_price', 'amount'
        '_parent_sale.sale_discount', 'descuento_desglose', 'taxes', 'product')
    def on_change_discount(self):
        return self.update_prices()

    @fields.depends('gross_unit_price', 'descuento_desglose', 'unit_price', 'amount'
        '_parent_sale.sale_discount', 'discount', 'taxes', 'product', 'quantity')
    def on_change_descuento_desglose(self):
        return self.update_prices()

    @fields.depends('discount', '_parent_sale.sale_discount',
        'descuento_desglose')
    def on_change_product(self):
        res = super(SaleLine, self).on_change_product()
        if 'unit_price' in res:
            self.gross_unit_price = res['unit_price']
            self.discount = Decimal(0)
            self.descuento_desglose = Decimal(0)
            res.update(self.update_prices())
        if 'discount' not in res:
            res['discount'] = Decimal(0)
        if 'descuento_desglose' not in res:
            res['descuento_desglose'] = Decimal(0)
        return res

    @fields.depends('discount', '_parent_sale.sale_discount',
        'descuento_desglose', 'taxes', 'product')
    def on_change_quantity(self):
        res = super(SaleLine, self).on_change_quantity()
        if 'unit_price' in res:
            self.gross_unit_price = res['gross_unit_price']
            res.update(self.update_prices())
        return res
