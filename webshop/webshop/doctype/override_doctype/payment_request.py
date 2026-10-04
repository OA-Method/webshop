import frappe
from frappe.utils import get_url

from erpnext.accounts.doctype.payment_request.payment_request import (
    PaymentRequest as OriginalPaymentRequest,
)


class PaymentRequest(OriginalPaymentRequest):
    def on_payment_authorized(self, status=None):
        # Settlement (creating the Payment Entry that clears the linked doc) is
        # base behaviour and must happen regardless of whether Webshop is
        # enabled -- delegate to erpnext's PaymentRequest.on_payment_authorized
        # for that. (framework#107: this override used to return early when
        # Webshop Settings was disabled, silently shadowing settlement for
        # every gateway -- PayFast included -- since this subclass is what
        # frappe.get_doc("Payment Request", ...) always instantiates once
        # webshop is installed.) The redirect below is only an enabled-cart
        # convenience layered on top of that settlement.
        redirect_to = super().on_payment_authorized(status)

        if status not in ("Authorized", "Completed"):
            return redirect_to

        if not hasattr(frappe.local, "session"):
            return redirect_to

        if frappe.local.session.user == "Guest":
            return redirect_to

        cart_settings = frappe.get_doc("Webshop Settings")

        if not cart_settings.enabled:
            return redirect_to

        success_url = cart_settings.payment_success_url
        redirect_to = get_url("/orders/{0}".format(self.reference_name))

        if success_url:
            redirect_to = (
                {
                    "Orders": "/orders",
                    "Invoices": "/invoices",
                    "My Account": "/me",
                }
            ).get(success_url, "/me")

        return redirect_to

    @staticmethod
    def get_gateway_details(args):
        if args.order_type != "Shopping Cart":
            return super().get_gateway_details(args)

        cart_settings = frappe.get_doc("Webshop Settings")
        gateway_account = cart_settings.payment_gateway_account
        return super().get_payment_gateway_account(gateway_account)
