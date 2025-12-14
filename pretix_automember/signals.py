import logging
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from pretix.control.signals import nav_organizer
from pretix.base.signals import customer_signed_in
from pretix.base.models.customers import Customer
from pretix.base.models.memberships import Membership, MembershipType
from datetime import datetime, timedelta
from django.utils import timezone
import pytz

logger = logging.getLogger(__name__)

@receiver(nav_organizer, dispatch_uid="pretix_automember_nav_organizer_settings")
def navbar_organizer_settings(sender, request, **kwargs):
    url = reverse('plugins:pretix_automember:org_settings', kwargs={
        'organizer': request.organizer.slug
    })
    
    if not request.resolver_match:
        return []

    return [{
        'label': _('Automember'),
        'url': url,
        'active': request.resolver_match.url_name == 'org_settings' and request.resolver_match.namespace == 'plugins:pretix_automember',
        'icon': 'id-card',
    }]

@receiver(customer_signed_in, dispatch_uid="pretix_automember_customer_signed_in")
def customer_signed_in_handler(customer: Customer, sender, **kwargs):
    organizer = sender
    if not organizer:
        return

    if not organizer.settings.get('automember_enabled', as_type=bool):
        return

    membership_type_id = organizer.settings.get('automember_membership_id')
    if not membership_type_id:
        return

    try:
        membership_type = MembershipType.objects.get(id=membership_type_id, organizer=organizer)
    except MembershipType.DoesNotExist:
        logger.exception("Configured membership not found")
        return
    
    limit_to_sso_sign_ins = organizer.settings.get('automember_limit_assignment_to_sso', as_type=bool)
    logger.warning(f"Setting: {limit_to_sso_sign_ins=}")
    if limit_to_sso_sign_ins:
        allowed_sso_providers = organizer.settings.get('automember_sso_ids', as_type=list)
        if customer.provider is None:
            return
        if customer.provider.id not in allowed_sso_providers:
            return

    # Calculate expiry date based on semester
    now = timezone.now()

    try:
        organizer_tz = pytz.timezone(organizer.settings.timezone)
    except pytz.UnknownTimeZoneError:
        # Fallback to UTC if the timezone is invalid for some reason
        organizer_tz = pytz.utc

    tz_now = now.astimezone(organizer_tz)
    
    duration_type = organizer.settings.get('automember_duration_type', default='semester')

    if duration_type == 'semester':
        if 4 <= tz_now.month <= 9:
            # Summer semester
            naive_expiry_date = datetime(tz_now.year, 9, 30, 23, 59, 59)
        else:
            # Winter semester
            if tz_now.month >= 10:
                naive_expiry_date = datetime(tz_now.year + 1, 3, 31, 23, 59, 59)
            else:
                naive_expiry_date = datetime(tz_now.year, 3, 31, 23, 59, 59)
        expiry_date = organizer_tz.localize(naive_expiry_date)
    elif duration_type == 'days':
        duration_days = organizer.settings.get('automember_duration_days', as_type=int)
        if not duration_days:
            return
        expiry_date = now + timedelta(days=duration_days)
    else:
        return

    # Check for existing membership
    try:
        membership = Membership.objects.get(customer=customer, membership_type=membership_type, testmode=False)
        # Membership exists, check if expired
        if membership.date_end < now:
            # Extend membership
            membership.date_end = expiry_date
            membership.save()
    except Membership.DoesNotExist:
        # Create new membership
        Membership.objects.create(
            customer=customer,
            membership_type=membership_type,
            date_start=now,
            date_end=expiry_date
        )
