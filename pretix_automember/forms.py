from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from pretix.base.models.memberships import MembershipType
from pretix.base.models.customers import CustomerSSOProvider

class AutomemberSettingsForm(forms.Form):
    # General Settings
    plugin_enabled = forms.BooleanField(
        label=_("Enable plugin for this organizer"),
        initial=False,
        required=False
    )
    membership_id = forms.ChoiceField(
        label=_("Membership"),
        required=False,
        help_text=_("What membership to assign on login")
    )

    # SSO Settings
    limit_assignment_to_sso = forms.ChoiceField(
        label=_("Only Assign when logging in with a Single Sign On Provider")
    )

    sso_ids = forms.MultipleChoiceField(
        label=_("Allowed Single Sign On Providers"),
        required=False,
        help_text=_("What single sign providers need to be used to gain the membership")
    )

    # Duration Settings
    DURATION_CHOICES = [
        ('semester', _("Until the end of the semester")),
        ('days', _("For a specific number of days")),
    ]
    duration_type = forms.ChoiceField(
        label=_("Membership Duration"),
        choices=DURATION_CHOICES,
        widget=forms.RadioSelect,
        initial='semester',
    )
    duration_days = forms.IntegerField(
        label=_("Number of days"),
        required=False,
        help_text=_("Only used if 'specific number of days' is selected above."),
        min_value=1
    )

    def __init__(self, *args, **kwargs):
        organizer = kwargs.pop('organizer')
        super().__init__(*args, **kwargs)
        self.fields['membership_id'].choices = [
            (m.id, m.name) for m in MembershipType.objects.filter(organizer=organizer)
        ]
        self.fields['sso_ids'].choices = [
            (sso.id, sso.name) for sso in CustomerSSOProvider.objects.filter(organizer=organizer)
        ]

    def clean(self):
        cleaned_data = super().clean()
        duration_type = cleaned_data.get('duration_type')
        duration_days = cleaned_data.get('duration_days')

        if duration_type == 'days' and not duration_days:
            raise ValidationError(
                _("You must specify the number of days if you select that option."),
                code='days_required'
            )
        return cleaned_data
