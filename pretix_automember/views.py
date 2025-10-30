from django.views.generic import FormView
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from pretix.control.views.organizer import OrganizerDetailViewMixin

from .forms import AutomemberSettingsForm

class AutomemberSettingsView(OrganizerDetailViewMixin, FormView):
    template_name = 'pretix_automember/settings.html'
    form_class = AutomemberSettingsForm
    permission = 'can_change_organizer_settings'
    
    def get_success_url(self):
        return reverse('plugins:pretix_automember:org_settings', kwargs={
            'organizer': self.request.organizer.slug,
        })

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organizer'] = self.request.organizer
        # Pre-fill the form with currently saved settings
        kwargs['initial'] = {
            'plugin_enabled': self.request.organizer.settings.get('automember_enabled', as_type=bool),
            'membership_id': self.request.organizer.settings.get('automember_membership_id'),
            'limit_assignment_to_sso': self.request.organizer.settings.get('automember_limit_assignment_to_sso', as_type=bool),
            'sso_ids': self.request.organizer.settings.get('automember_sso_ids', as_type=list),
            'duration_type': self.request.organizer.settings.get('automember_duration_type', default='semester'),
            'duration_days': self.request.organizer.settings.get('automember_duration_days', as_type=int),
        }
        return kwargs

    def form_valid(self, form):
        # Save the settings
        self.request.organizer.settings.set('automember_enabled', form.cleaned_data['plugin_enabled'])
        self.request.organizer.settings.set('automember_membership_id', form.cleaned_data['membership_id'])
        self.request.organizer.settings.set('automember_duration_type', form.cleaned_data['duration_type'])
        self.request.organizer.settings.set('automember_limit_assignment_to_sso', form.cleaned_data['limit_assignment_to_sso'])
        self.request.organizer.settings.set('automember_sso_ids', form.cleaned_data['sso_ids'])
        
        if form.cleaned_data['duration_type'] == 'days':
            self.request.organizer.settings.set('automember_duration_days', form.cleaned_data['duration_days'])
        else:
            # Clean up the days value if not used
            self.request.organizer.settings.delete('automember_duration_days')

        messages.success(self.request, _('Your settings have been saved.'))
        return super().form_valid(form)
