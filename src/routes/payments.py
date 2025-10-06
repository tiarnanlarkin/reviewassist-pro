from flask import Blueprint, request, jsonify, current_app, url_for
from flask_cors import cross_origin
import stripe
import json
import logging
from datetime import datetime, timedelta
from src.models.user import db
from src.models.auth import AuthUser
from src.models.subscription import (
    SubscriptionPlan, UserSubscription, SubscriptionStatus, 
    BillingCycle, PlanType, FeatureUsage, FeatureType
)
from src.routes.auth import token_required
from sqlalchemy import func

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

payments_bp = Blueprint('payments', __name__, url_prefix='/api/payments')

# Initialize Stripe
def init_stripe():
    stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
    if not stripe.api_key:
        logger.warning("Stripe API key not configured")

@payments_bp.before_request
def before_request():
    init_stripe()

# Subscription Management Endpoints

@payments_bp.route('/create-subscription', methods=['POST'])
@cross_origin()
@token_required
def create_subscription(current_user):
    """Create a new subscription for the user"""
    try:
        data = request.get_json()
        plan_id = data.get('plan_id')
        billing_cycle = data.get('billing_cycle', 'monthly')
        payment_method_id = data.get('payment_method_id')
        
        # Get subscription plan
        plan = SubscriptionPlan.query.get(plan_id)
        if not plan:
            return jsonify({'error': 'Invalid subscription plan'}), 400
            
        # Check if user already has an active subscription
        existing_subscription = UserSubscription.query.filter_by(
            user_id=current_user.id,
            status=SubscriptionStatus.ACTIVE
        ).first()
        
        if existing_subscription:
            return jsonify({'error': 'User already has an active subscription'}), 400
        
        # Create Stripe customer if doesn't exist
        if not current_user.stripe_customer_id:
            stripe_customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.full_name,
                metadata={'user_id': current_user.id}
            )
            current_user.stripe_customer_id = stripe_customer.id
            db.session.commit()
        
        # Attach payment method to customer
        if payment_method_id:
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=current_user.stripe_customer_id
            )
            
            # Set as default payment method
            stripe.Customer.modify(
                current_user.stripe_customer_id,
                invoice_settings={'default_payment_method': payment_method_id}
            )
        
        # Determine price based on billing cycle
        price = plan.monthly_price if billing_cycle == 'monthly' else plan.annual_price
        
        # Create Stripe subscription
        stripe_subscription = stripe.Subscription.create(
            customer=current_user.stripe_customer_id,
            items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'{plan.name} Plan',
                        'description': plan.description
                    },
                    'unit_amount': int(price * 100),  # Convert to cents
                    'recurring': {
                        'interval': 'month' if billing_cycle == 'monthly' else 'year'
                    }
                }
            }],
            payment_behavior='default_incomplete',
            payment_settings={'save_default_payment_method': 'on_subscription'},
            expand=['latest_invoice.payment_intent'],
            trial_period_days=14,  # 14-day free trial
            metadata={
                'user_id': current_user.id,
                'plan_id': plan_id,
                'billing_cycle': billing_cycle
            }
        )
        
        # Create local subscription record
        subscription = UserSubscription(
            user_id=current_user.id,
            plan_id=plan_id,
            stripe_subscription_id=stripe_subscription.id,
            status=SubscriptionStatus.TRIALING,
            billing_cycle=BillingCycle(billing_cycle),
            current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start),
            current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end),
            trial_end=datetime.fromtimestamp(stripe_subscription.trial_end) if stripe_subscription.trial_end else None
        )
        
        db.session.add(subscription)
        db.session.commit()
        
        return jsonify({
            'subscription_id': subscription.id,
            'stripe_subscription_id': stripe_subscription.id,
            'client_secret': stripe_subscription.latest_invoice.payment_intent.client_secret,
            'status': subscription.status.value,
            'trial_end': subscription.trial_end.isoformat() if subscription.trial_end else None
        })
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating subscription: {str(e)}")
        return jsonify({'error': f'Payment processing error: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        return jsonify({'error': 'Failed to create subscription'}), 500

@payments_bp.route('/upgrade-subscription', methods=['POST'])
@cross_origin()
@token_required
def upgrade_subscription(current_user):
    """Upgrade user's subscription to a higher plan"""
    try:
        data = request.get_json()
        new_plan_id = data.get('plan_id')
        billing_cycle = data.get('billing_cycle')
        
        # Get current subscription
        current_subscription = UserSubscription.query.filter_by(
            user_id=current_user.id,
            status=SubscriptionStatus.ACTIVE
        ).first()
        
        if not current_subscription:
            return jsonify({'error': 'No active subscription found'}), 400
        
        # Get new plan
        new_plan = SubscriptionPlan.query.get(new_plan_id)
        if not new_plan:
            return jsonify({'error': 'Invalid subscription plan'}), 400
        
        # Update Stripe subscription
        stripe_subscription = stripe.Subscription.retrieve(current_subscription.stripe_subscription_id)
        
        # Calculate new price
        new_price = new_plan.monthly_price if billing_cycle == 'monthly' else new_plan.annual_price
        
        # Update subscription items
        stripe.Subscription.modify(
            current_subscription.stripe_subscription_id,
            items=[{
                'id': stripe_subscription['items']['data'][0].id,
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'{new_plan.name} Plan',
                        'description': new_plan.description
                    },
                    'unit_amount': int(new_price * 100),
                    'recurring': {
                        'interval': 'month' if billing_cycle == 'monthly' else 'year'
                    }
                }
            }],
            proration_behavior='create_prorations',
            metadata={
                'user_id': current_user.id,
                'plan_id': new_plan_id,
                'billing_cycle': billing_cycle
            }
        )
        
        # Update local subscription record
        current_subscription.plan_id = new_plan_id
        current_subscription.billing_cycle = BillingCycle(billing_cycle)
        current_subscription.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Subscription upgraded successfully',
            'subscription_id': current_subscription.id,
            'new_plan': new_plan.name
        })
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error upgrading subscription: {str(e)}")
        return jsonify({'error': f'Payment processing error: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error upgrading subscription: {str(e)}")
        return jsonify({'error': 'Failed to upgrade subscription'}), 500

@payments_bp.route('/cancel-subscription', methods=['POST'])
@cross_origin()
@token_required
def cancel_subscription(current_user):
    """Cancel user's subscription"""
    try:
        data = request.get_json()
        immediate = data.get('immediate', False)
        
        # Get current subscription
        subscription = UserSubscription.query.filter_by(
            user_id=current_user.id,
            status=SubscriptionStatus.ACTIVE
        ).first()
        
        if not subscription:
            return jsonify({'error': 'No active subscription found'}), 400
        
        if immediate:
            # Cancel immediately
            stripe.Subscription.delete(subscription.stripe_subscription_id)
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.utcnow()
        else:
            # Cancel at period end
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
            subscription.cancel_at_period_end = True
        
        db.session.commit()
        
        return jsonify({
            'message': 'Subscription canceled successfully',
            'immediate': immediate,
            'ends_at': subscription.current_period_end.isoformat()
        })
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error canceling subscription: {str(e)}")
        return jsonify({'error': f'Payment processing error: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error canceling subscription: {str(e)}")
        return jsonify({'error': 'Failed to cancel subscription'}), 500

# Payment Method Management

@payments_bp.route('/payment-methods', methods=['GET'])
@cross_origin()
@token_required
def get_payment_methods(current_user):
    """Get user's payment methods"""
    try:
        if not current_user.stripe_customer_id:
            return jsonify({'payment_methods': []})
        
        # Get payment methods from Stripe
        payment_methods = stripe.PaymentMethod.list(
            customer=current_user.stripe_customer_id,
            type='card'
        )
        
        methods = []
        for pm in payment_methods.data:
            methods.append({
                'id': pm.id,
                'brand': pm.card.brand,
                'last4': pm.card.last4,
                'exp_month': pm.card.exp_month,
                'exp_year': pm.card.exp_year,
                'is_default': pm.id == stripe.Customer.retrieve(current_user.stripe_customer_id).invoice_settings.default_payment_method
            })
        
        return jsonify({'payment_methods': methods})
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error getting payment methods: {str(e)}")
        return jsonify({'error': f'Payment processing error: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error getting payment methods: {str(e)}")
        return jsonify({'error': 'Failed to get payment methods'}), 500

@payments_bp.route('/add-payment-method', methods=['POST'])
@cross_origin()
@token_required
def add_payment_method(current_user):
    """Add a new payment method"""
    try:
        data = request.get_json()
        payment_method_id = data.get('payment_method_id')
        set_as_default = data.get('set_as_default', False)
        
        if not current_user.stripe_customer_id:
            return jsonify({'error': 'No customer record found'}), 400
        
        # Attach payment method to customer
        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=current_user.stripe_customer_id
        )
        
        # Set as default if requested
        if set_as_default:
            stripe.Customer.modify(
                current_user.stripe_customer_id,
                invoice_settings={'default_payment_method': payment_method_id}
            )
        
        return jsonify({'message': 'Payment method added successfully'})
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error adding payment method: {str(e)}")
        return jsonify({'error': f'Payment processing error: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error adding payment method: {str(e)}")
        return jsonify({'error': 'Failed to add payment method'}), 500

@payments_bp.route('/remove-payment-method', methods=['DELETE'])
@cross_origin()
@token_required
def remove_payment_method(current_user):
    """Remove a payment method"""
    try:
        data = request.get_json()
        payment_method_id = data.get('payment_method_id')
        
        # Detach payment method
        stripe.PaymentMethod.detach(payment_method_id)
        
        return jsonify({'message': 'Payment method removed successfully'})
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error removing payment method: {str(e)}")
        return jsonify({'error': f'Payment processing error: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error removing payment method: {str(e)}")
        return jsonify({'error': 'Failed to remove payment method'}), 500

# Billing Portal

@payments_bp.route('/create-portal-session', methods=['POST'])
@cross_origin()
@token_required
def create_portal_session(current_user):
    """Create Stripe Customer Portal session"""
    try:
        if not current_user.stripe_customer_id:
            return jsonify({'error': 'No customer record found'}), 400
        
        # Create portal session
        session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=request.json.get('return_url', request.host_url)
        )
        
        return jsonify({'url': session.url})
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating portal session: {str(e)}")
        return jsonify({'error': f'Payment processing error: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error creating portal session: {str(e)}")
        return jsonify({'error': 'Failed to create portal session'}), 500

# Invoices and Billing

@payments_bp.route('/invoices', methods=['GET'])
@cross_origin()
@token_required
def get_invoices(current_user):
    """Get user's invoices"""
    try:
        if not current_user.stripe_customer_id:
            return jsonify({'invoices': []})
        
        # Get invoices from Stripe
        invoices = stripe.Invoice.list(
            customer=current_user.stripe_customer_id,
            limit=20
        )
        
        invoice_list = []
        for invoice in invoices.data:
            invoice_list.append({
                'id': invoice.id,
                'amount_paid': invoice.amount_paid / 100,  # Convert from cents
                'amount_due': invoice.amount_due / 100,
                'currency': invoice.currency,
                'status': invoice.status,
                'created': datetime.fromtimestamp(invoice.created).isoformat(),
                'due_date': datetime.fromtimestamp(invoice.due_date).isoformat() if invoice.due_date else None,
                'invoice_pdf': invoice.invoice_pdf,
                'hosted_invoice_url': invoice.hosted_invoice_url
            })
        
        return jsonify({'invoices': invoice_list})
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error getting invoices: {str(e)}")
        return jsonify({'error': f'Payment processing error: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error getting invoices: {str(e)}")
        return jsonify({'error': 'Failed to get invoices'}), 500

# Webhook Handler

@payments_bp.route('/webhook', methods=['POST'])
@cross_origin()
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        logger.error("Invalid payload in webhook")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature in webhook")
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    try:
        if event['type'] == 'customer.subscription.created':
            handle_subscription_created(event['data']['object'])
        elif event['type'] == 'customer.subscription.updated':
            handle_subscription_updated(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            handle_subscription_deleted(event['data']['object'])
        elif event['type'] == 'invoice.payment_succeeded':
            handle_payment_succeeded(event['data']['object'])
        elif event['type'] == 'invoice.payment_failed':
            handle_payment_failed(event['data']['object'])
        else:
            logger.info(f"Unhandled event type: {event['type']}")
    
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}")
        return jsonify({'error': 'Webhook handling failed'}), 500
    
    return jsonify({'status': 'success'})

def handle_subscription_created(subscription):
    """Handle subscription created webhook"""
    user_id = subscription['metadata'].get('user_id')
    if user_id:
        db_subscription = UserSubscription.query.filter_by(
            stripe_subscription_id=subscription['id']
        ).first()
        
        if db_subscription:
            db_subscription.status = SubscriptionStatus(subscription['status'])
            db.session.commit()
            logger.info(f"Updated subscription status for user {user_id}")

def handle_subscription_updated(subscription):
    """Handle subscription updated webhook"""
    db_subscription = UserSubscription.query.filter_by(
        stripe_subscription_id=subscription['id']
    ).first()
    
    if db_subscription:
        db_subscription.status = SubscriptionStatus(subscription['status'])
        db_subscription.current_period_start = datetime.fromtimestamp(subscription['current_period_start'])
        db_subscription.current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
        
        if subscription.get('canceled_at'):
            db_subscription.canceled_at = datetime.fromtimestamp(subscription['canceled_at'])
        
        db.session.commit()
        logger.info(f"Updated subscription {subscription['id']}")

def handle_subscription_deleted(subscription):
    """Handle subscription deleted webhook"""
    db_subscription = UserSubscription.query.filter_by(
        stripe_subscription_id=subscription['id']
    ).first()
    
    if db_subscription:
        db_subscription.status = SubscriptionStatus.CANCELED
        db_subscription.canceled_at = datetime.utcnow()
        db.session.commit()
        logger.info(f"Canceled subscription {subscription['id']}")

def handle_payment_succeeded(invoice):
    """Handle successful payment webhook"""
    subscription_id = invoice.get('subscription')
    if subscription_id:
        db_subscription = UserSubscription.query.filter_by(
            stripe_subscription_id=subscription_id
        ).first()
        
        if db_subscription:
            # Create invoice record
            invoice_record = Invoice(
                user_id=db_subscription.user_id,
                subscription_id=db_subscription.id,
                stripe_invoice_id=invoice['id'],
                amount=invoice['amount_paid'] / 100,
                currency=invoice['currency'],
                status='paid',
                invoice_date=datetime.fromtimestamp(invoice['created']),
                due_date=datetime.fromtimestamp(invoice['due_date']) if invoice.get('due_date') else None
            )
            
            db.session.add(invoice_record)
            db.session.commit()
            logger.info(f"Created invoice record for subscription {subscription_id}")

def handle_payment_failed(invoice):
    """Handle failed payment webhook"""
    subscription_id = invoice.get('subscription')
    if subscription_id:
        db_subscription = UserSubscription.query.filter_by(
            stripe_subscription_id=subscription_id
        ).first()
        
        if db_subscription:
            # Update subscription status if needed
            if invoice['attempt_count'] >= 3:
                db_subscription.status = SubscriptionStatus.PAST_DUE
                db.session.commit()
            
            logger.warning(f"Payment failed for subscription {subscription_id}")

# Usage Tracking

@payments_bp.route('/usage/<feature>', methods=['GET'])
@cross_origin()
@token_required
def get_usage(current_user, feature):
    """Get current usage for a feature"""
    try:
        subscription = UserSubscription.query.filter_by(
            user_id=current_user.id,
            status=SubscriptionStatus.ACTIVE
        ).first()
        
        if not subscription:
            return jsonify({'error': 'No active subscription'}), 400
        
        # Get current usage
        usage = SubscriptionUsage.query.filter_by(
            subscription_id=subscription.id,
            feature_type=FeatureType(feature),
            period_start=subscription.current_period_start
        ).first()
        
        current_usage = usage.usage_count if usage else 0
        
        # Get plan limits
        plan_feature = subscription.plan.features.filter_by(
            feature_type=FeatureType(feature)
        ).first()
        
        limit = plan_feature.limit_value if plan_feature else 0
        
        return jsonify({
            'feature': feature,
            'current_usage': current_usage,
            'limit': limit,
            'percentage_used': (current_usage / limit * 100) if limit > 0 else 0
        })
        
    except Exception as e:
        logger.error(f"Error getting usage: {str(e)}")
        return jsonify({'error': 'Failed to get usage'}), 500

@payments_bp.route('/subscription/status', methods=['GET'])
@cross_origin()
@token_required
def get_subscription_status(current_user):
    """Get user's subscription status"""
    try:
        subscription = UserSubscription.query.filter_by(
            user_id=current_user.id
        ).order_by(UserSubscription.created_at.desc()).first()
        
        if not subscription:
            return jsonify({
                'has_subscription': False,
                'status': 'none'
            })
        
        return jsonify({
            'has_subscription': True,
            'subscription_id': subscription.id,
            'plan_name': subscription.plan.name,
            'status': subscription.status.value,
            'billing_cycle': subscription.billing_cycle.value,
            'current_period_start': subscription.current_period_start.isoformat(),
            'current_period_end': subscription.current_period_end.isoformat(),
            'trial_end': subscription.trial_end.isoformat() if subscription.trial_end else None,
            'cancel_at_period_end': subscription.cancel_at_period_end,
            'canceled_at': subscription.canceled_at.isoformat() if subscription.canceled_at else None
        })
        
    except Exception as e:
        logger.error(f"Error getting subscription status: {str(e)}")
        return jsonify({'error': 'Failed to get subscription status'}), 500

