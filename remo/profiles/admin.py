from socket import error as socket_error

from django.conf.urls import patterns, url
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from import_export import fields, resources
from import_export.admin import ExportMixin
from functools import update_wrapper

from remo.profiles.models import (FunctionalArea, UserAvatar, UserProfile,
                                  UserStatus)
from remo.profiles.tasks import check_celery

# Unregister User from Administration to attach UserProfileInline
admin.site.unregister(User)


class UserProfileFilter(SimpleListFilter):
    title = 'has associated profile'
    parameter_name = 'has_userprofile'

    def lookups(self, request, model_admin):
        return (('False', 'No'), ('True', 'Yes'))

    def queryset(self, request, queryset):
        if self.value() == 'False':
            return queryset.filter(userprofile__isnull=True)
        elif self.value() == 'True':
            return queryset.filter(userprofile__isnull=False)
        return queryset


class RepProfileFilter(SimpleListFilter):
    title = 'Rep profiles'
    parameter_name = 'rep_profile'

    def lookups(self, request, model_admin):
        return (('False', 'No'), ('True', 'Yes'))

    def queryset(self, request, queryset):
        if self.value() == 'True':
            return queryset.filter(groups__name='Rep')
        elif self.value() == 'False':
            return queryset.exclude(groups__name='Rep')
        return queryset


class MozillianProfileFilter(SimpleListFilter):
    title = 'Mozillian profiles'
    parameter_name = 'mozillian_profile'

    def lookups(self, request, model_admin):
        return (('False', 'No'), ('True', 'Yes'))

    def queryset(self, request, queryset):
        if self.value() == 'True':
            return queryset.filter(groups__name='Mozillians')
        elif self.value() == 'False':
            return queryset.exclude(groups__name='Mozillians')
        return queryset


class MentorProfileFilter(SimpleListFilter):
    title = 'Mentor profiles'
    parameter_name = 'mentor_profile'

    def lookups(self, request, model_admin):
        return (('False', 'No'), ('True', 'Yes'))

    def queryset(self, request, queryset):
        if self.value() == 'True':
            return queryset.filter(groups__name='Mentor')
        elif self.value() == 'False':
            return queryset.exclude(groups__name='Mentor')
        return queryset


class CouncilProfileFilter(SimpleListFilter):
    title = 'Council profiles'
    parameter_name = 'council_profile'

    def lookups(self, request, model_admin):
        return (('False', 'No'), ('True', 'Yes'))

    def queryset(self, request, queryset):
        if self.value() == 'True':
            return queryset.filter(groups__name='Council')
        elif self.value() == 'False':
            return queryset.exclude(groups__name='Council')
        return queryset


class AlumniProfileFilter(SimpleListFilter):
    title = 'Alumni profiles'
    parameter_name = 'alumni_profile'

    def lookups(self, request, model_admin):
        return (('False', 'No'), ('True', 'Yes'))

    def queryset(self, request, queryset):
        if self.value() == 'True':
            return queryset.filter(groups__name='Alumni')
        elif self.value() == 'False':
            return queryset.exclude(groups__name='Alumni')
        return queryset


class AdminProfileFilter(SimpleListFilter):
    title = 'Admin profiles'
    parameter_name = 'admin_profile'

    def lookups(self, request, model_admin):
        return (('False', 'No'), ('True', 'Yes'))

    def queryset(self, request, queryset):
        if self.value() == 'True':
            return queryset.filter(groups__name='Admin')
        elif self.value() == 'False':
            return queryset.exclude(groups__name='Admin')
        return queryset


class ActivityCampaign(SimpleListFilter):
    title = 'Activity Campaign'
    parameter_name = 'activity_campaign_2015'

    def lookups(self, request, model_admin):
        return (('False', 'No'), ('True', 'Yes'))

    def queryset(self, request, queryset):
        if self.value() == 'True':
            return queryset.filter(ng_reports__report_date__gte='2015-10-01')
        elif self.value() == 'False':
            return queryset.exclude(ng_reports__report_date__gte='2015-10-01')
        return queryset


class UserResource(resources.ModelResource):
    personal_emails = fields.Field()
    country = fields.Field()
    mentor = fields.Field()
    date_joined_program = fields.Field()
    date_left_program = fields.Field()
    display_name = fields.Field()

    class Meta:
        model = User
        export_order = ['id', 'username', 'first_name', 'last_name', 'email',
                        'personal_emails', 'password', 'is_staff', 'is_active',
                        'is_superuser', 'last_login', 'groups',
                        'user_permissions', 'country', 'mentor',
                        'date_joined_program', 'date_left_program', 'display_name']

    def dehydrate_personal_emails(self, user):
        return user.userprofile.private_email

    def dehydrate_country(self, user):
        return user.userprofile.country

    def dehydrate_mentor(self, user):
        if (user.userprofile.mentor
                and user.groups.filter(name='Rep').exists()):
            return user.userprofile.mentor.get_full_name()
        return ''

    def dehydrate_date_joined_program(self, user):
        date_joined = user.userprofile.date_joined_program
        if date_joined:
            return date_joined.strftime('%d %B %Y')
        return None

    def dehydrate_date_left_program(self, user):
        date_left = user.userprofile.date_left_program
        if date_left:
            return date_left.strftime('%d %B %Y')
        return None

    def dehydrate_display_name(self, user):
        if not user.userprofile.display_name:
            return ''
        return user.userprofile.display_name


class UserProfileInline(admin.StackedInline):
    """ReportLink Inline."""
    model = UserProfile
    readonly_fields = ['unavailability_task_id']
    fk_name = 'user'


class UserAdmin(ExportMixin, UserAdmin):
    """User Admin."""
    resource_class = UserResource
    inlines = [UserProfileInline]
    list_filter = (UserAdmin.list_filter
                   + ('userprofile__registration_complete', RepProfileFilter,
                      MozillianProfileFilter, MentorProfileFilter,
                      CouncilProfileFilter, AlumniProfileFilter,
                      AdminProfileFilter, ActivityCampaign,
                      'userprofile__is_rotm_nominee',
                      'userprofile__date_joined_program',
                      'ng_reports__report_date', UserProfileFilter))
    list_display = UserAdmin.list_display + ('get_groups',)
    search_fields = (UserAdmin.search_fields + ('userprofile__country',))

    def get_groups(self, obj):
        user_groups = [group.name for group in obj.groups.all()]
        return (', ').join(user_groups)
    get_groups.short_description = 'Groups'

    def get_urls(self):
        """Return custom and UserAdmin urls."""

        def wrap(view):

            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        urls = super(UserAdmin, self).get_urls()
        my_urls = patterns('', url(r'check_celery', wrap(self.check_celery),
                                   name='users_check_celery'))
        return my_urls + urls

    def check_celery(self, request):
        try:
            investigator = check_celery.delay()
        except socket_error as e:
            messages.error(request, 'Cannot connect to broker: %s' % e)
            return HttpResponseRedirect(reverse('admin:auth_user_changelist'))

        try:
            investigator.get(timeout=5)
        except investigator.TimeoutError as e:
            messages.error(request, 'Worker timeout: %s' % e)
        else:
            messages.success(request, 'Celery is OK')
        finally:
            return HttpResponseRedirect(reverse('admin:auth_user_changelist'))


class UserAvatarResource(resources.ModelResource):
    user = fields.Field()

    class Meta:
        model = UserAvatar

    def dehydrate_user(self, useravatar):
        return useravatar.user.get_full_name()


class UserAvatarAdmin(ExportMixin, admin.ModelAdmin):
    """UserAvatar Admin."""
    resource_class = UserAvatarResource
    list_display = ('display_name', 'avatar_url', 'last_update')

    def display_name(self, obj):
        return obj.user.userprofile.display_name


class FunctionalAreaAdmin(ExportMixin, admin.ModelAdmin):
    """FunctionalArea Admin."""
    list_display = ('name', 'registered_reps', 'registered_mozillians',
                    'registered_events', 'active')

    def registered_reps(self, obj):
        return obj.users_matching.count()

    def registered_mozillians(self, obj):
        return obj.users_tracking.count()

    def registered_events(self, obj):
        return obj.events_categories.count()

    def queryset(self, request):
        return self.model.objects.get_query_set()


class UserStatusFilter(SimpleListFilter):
    title = 'User Statuses'
    parameter_name = 'user_status'

    def lookups(self, request, model_admin):
        return (('False', 'No'), ('True', 'Yes'))

    def queryset(self, request, queryset):
        if self.value() == 'True':
            return queryset.filter(is_unavailable=True)
        elif self.value() == 'False':
            return queryset.filter(is_unavailable=False)
        return queryset


class UserStatusResource(resources.ModelResource):
    user = fields.Field()
    replacement_rep = fields.Field()

    class Meta:
        model = UserStatus

    def dehydrate_user(self, userstatus):
        return userstatus.user.get_full_name()

    def dehydrate_replacement_rep(self, userstatus):
        if userstatus.replacement_rep:
            return userstatus.replacement_rep.get_full_name()
        return None


class UserStatusAdmin(ExportMixin, admin.ModelAdmin):
    """User Status Admin."""
    resource_class = UserStatusResource
    model = UserStatus
    list_display = ('user', 'start_date', 'expected_date', 'return_date',
                    'created_on', 'replacement_rep')
    search_fields = ['user__first_name', 'user__last_name',
                     'user__userprofile__display_name']
    list_filter = (UserStatusFilter,)


admin.site.register(User, UserAdmin)
admin.site.register(FunctionalArea, FunctionalAreaAdmin)
admin.site.register(UserAvatar, UserAvatarAdmin)
admin.site.register(UserStatus, UserStatusAdmin)
