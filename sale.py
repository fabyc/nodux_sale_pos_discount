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

__all__ = ['SaleLine']
__metaclass__ = PoolMeta


class SaleLine:
    __name__ = 'sale.line'

    
    @classmethod
    def __setup__(cls):
        super(SaleLine, cls).__setup__()

    def update_prices(self):
        unit_price = None
        gross_unit_price = gross_unit_price_wo_round = self.gross_unit_price
        sale_discount = Transaction().context.get('sale_discount')
        amount_w_tax = Transaction().context.get('total_amount_cache')
        
        
                
        if sale_discount == None:
            if self.sale and hasattr(self.sale, 'sale_discount'):
                sale_discount = self.sale.sale_discount or Decimal(0)
            else:
                sale_discount = Decimal(0)
                
        if sale_discount and self.sale.total_amount:
            total = self.sale.total_amount
            value = total - (sale_discount*100)
            sale_discount = ((value * 100) / total)/100
             
        if self.gross_unit_price is not None and (self.discount is not None
                or sale_discount is not None):
            unit_price = self.gross_unit_price
            if self.discount:
                unit_price *= (1 - self.discount)
            if sale_discount:
                unit_price *= (1 - sale_discount)
            
            if self.discount and sale_discount:
                discount = (self.discount + sale_discount
                    - self.discount * sale_discount)
                if discount != 1:
                    gross_unit_price_wo_round = unit_price / (1 - discount)
            elif self.discount and self.discount != 1:
                gross_unit_price_wo_round = unit_price / (1 - self.discount)
            elif sale_discount and sale_discount != 1:
                gross_unit_price_wo_round = unit_price / (1 - sale_discount)

            digits = self.__class__.unit_price.digits[1]
            unit_price = unit_price.quantize(Decimal(str(10.0 ** -digits)))

            digits = self.__class__.gross_unit_price.digits[1]
            gross_unit_price = gross_unit_price_wo_round.quantize(
                Decimal(str(10.0 ** -digits)))
        
        return {
            'gross_unit_price': gross_unit_price,
            'gross_unit_price_wo_round': gross_unit_price_wo_round,
            'unit_price': unit_price,
            }
            
            
                    
