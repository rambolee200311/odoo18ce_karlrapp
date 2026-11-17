from odoo import fields, models


class InboundOrder(models.Model):
    _inherit = 'world.depot.inbound.order'

    ginlong_owner_code = fields.Char(copy=False, index=True)
    ginlong_warehouse_code = fields.Char(copy=False)
    ginlong_business_type = fields.Char(copy=False, index=True)
    ginlong_sn_list_json = fields.Text(copy=False)


class InboundOrderProductPallet(models.Model):
    _inherit = 'world.depot.inbound.order.products.pallet'

    ginlong_product_code = fields.Char(copy=False, index=True)
    ginlong_product_name = fields.Char(copy=False)
    ginlong_specification_model = fields.Char(copy=False)


class InboundOrderProductSerialNumber(models.Model):
    _inherit = 'world.depot.inbound.order.product.serial.number'

    ginlong_quantity = fields.Float(copy=False)
    ginlong_pallet_code = fields.Char(copy=False, index=True)
    ginlong_product_code = fields.Char(copy=False, index=True)
    ginlong_product_name = fields.Char(copy=False)
    ginlong_specification_model = fields.Char(copy=False)


class OutboundOrder(models.Model):
    _inherit = 'world.depot.outbound.order'

    ginlong_owner_code = fields.Char(copy=False, index=True)
    ginlong_warehouse_code = fields.Char(copy=False)
    ginlong_business_type = fields.Char(copy=False, index=True)
    ginlong_customer = fields.Char(copy=False)
    ginlong_address = fields.Text(copy=False)
    ginlong_consignee = fields.Char(copy=False)
    ginlong_contact = fields.Char(copy=False)
    ginlong_contact_email = fields.Char(copy=False)
    ginlong_shipping_method = fields.Char(copy=False)


class OutboundOrderProduct(models.Model):
    _inherit = 'world.depot.outbound.order.product'

    ginlong_product_name = fields.Char(copy=False)
    ginlong_specification_model = fields.Char(copy=False)
    ginlong_order_no = fields.Char(copy=False)
    ginlong_unit = fields.Char(copy=False)
    ginlong_net_wt_machine = fields.Float(copy=False)
    ginlong_net_wt_total = fields.Float(copy=False)
    ginlong_pack_qty = fields.Float(copy=False)
    ginlong_pallet_qty = fields.Float(copy=False)
    ginlong_pallet_len = fields.Float(copy=False)
    ginlong_pallet_wid = fields.Float(copy=False)
    ginlong_pallet_hgt = fields.Float(copy=False)
    ginlong_unit_vol = fields.Float(copy=False)
    ginlong_pack_unit = fields.Char(copy=False)
    ginlong_pack_wt = fields.Float(copy=False)
    ginlong_pallet_total_wt = fields.Float(copy=False)
    ginlong_total_vol = fields.Float(copy=False)
    ginlong_carton_wt_total = fields.Float(copy=False)
    ginlong_gross_wt_total = fields.Float(copy=False)
    ginlong_standard = fields.Char(copy=False)
    ginlong_pack_mode = fields.Char(copy=False)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    ginlong_owner_code = fields.Char(copy=False, index=True)
    ginlong_specification_model = fields.Char(copy=False)
    ginlong_unit = fields.Char(copy=False)
    ginlong_weight = fields.Float(copy=False)
    ginlong_power = fields.Char(copy=False)
    ginlong_national_standard = fields.Char(copy=False)
    ginlong_certification_model = fields.Char(copy=False)
    ginlong_product_form = fields.Char(copy=False)
    ginlong_length = fields.Float(copy=False)
    ginlong_width = fields.Float(copy=False)
    ginlong_height = fields.Float(copy=False)
