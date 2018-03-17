from collections import namedtuple
from datetime import datetime, timedelta

from django.shortcuts import get_object_or_404
from django.utils.timezone import now

import django_filters
from rest_framework.views import APIView
from rest_framework.response import Response

from remo.api.views import BaseReadOnlyModelViewset
from remo.api.serializers import BaseKPISerializer
from remo.base.utils import get_quarter
from remo.reports.api.serializers import (ActivitiesDetailedSerializer,
                                          ActivitiesSerializer)
from remo.reports.models import NGReport


KPI_WEEKS = 12


class ActivitiesFilter(django_filters.FilterSet):
    user = django_filters.CharFilter(name='user__userprofile')
    activity = django_filters.CharFilter(name='activity__name')
    initiative = django_filters.CharFilter(name='campaign__name')
    mentor = django_filters.CharFilter(name='mentor__userprofile')
    category = django_filters.CharFilter(name='functional_areas__name')

    class Meta:
        model = NGReport
        fields = ('is_passive', 'event', 'activity_description', 'report_date',
                  'location', 'longitude', 'latitude', 'link',
                  'link_description')


class ActivitiesViewSet(BaseReadOnlyModelViewset):
    """Return a list of activities."""
    serializer_class = ActivitiesSerializer
    model = NGReport
    queryset = NGReport.objects.all()
    filter_class = ActivitiesFilter

    def retrieve(self, request, pk):
        report = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = ActivitiesDetailedSerializer(report,
                                                  context={'request': request})
        return Response(serializer.data)

    def get_queryset(self):
        orderby = self.request.query_params.get('orderby', 'DESC')

        if orderby == 'ASC':
            self.queryset = self.queryset.order_by('report_date')
        return self.queryset


class ActivitiesKPIFilter(django_filters.FilterSet):
    """Filter for activities KPI endpoint."""
    category = django_filters.CharFilter(name='functional_areas__name')
    initiative = django_filters.CharFilter(name='campaign__name')

    class Meta:
        model = NGReport
        fields = ['country', 'category', 'initiative']


class ActivitiesKPIView(APIView):

    def get(self, request):
        """Returns serialized data for Activities KPI"""

        qs = NGReport.objects.filter(report_date__lte=now())
        activities = ActivitiesKPIFilter(request.query_params, queryset=qs)
        weeks = int(request.query_params.get('weeks', KPI_WEEKS))

        # Total number of activities to day
        total = activities.qs.count()

        # Quarter calculations
        current_quarter_start = get_quarter()[1]

        # Total number of activities for current quarter
        quarter_total = activities.qs.filter(
            report_date__gte=current_quarter_start).count()

        # Total number of activities for the previous quarter
        previous_quarter_end = current_quarter_start - timedelta(days=1)
        previous_quarter_start = get_quarter(previous_quarter_end)[1]
        previous_quarter_total = activities.qs.filter(
            report_date__range=[previous_quarter_start,
                                previous_quarter_end]).count()

        diff = quarter_total - previous_quarter_total
        try:
            # Percentage change of activities since start of quarter
            percent_quarter = diff / float(previous_quarter_total)
        except ZeroDivisionError:
            if diff > 0:
                percent_quarter = 100
            else:
                percent_quarter = 0

        # Week calculations
        today = datetime.combine(now().date(), datetime.min.time())
        current_week_start = today - timedelta(days=now().weekday())
        prev_week_start = current_week_start - timedelta(weeks=1)

        # Total number of activities this week
        week_total = activities.qs.filter(
            report_date__gte=current_week_start).count()
        query_range = [prev_week_start, current_week_start]

        # Total number of activities for previous week
        prev_week_total = activities.qs.filter(
            report_date__range=query_range).count()

        diff = week_total - prev_week_total
        try:
            # Percentage change of activities compared with previous week
            percent_week = diff / float(prev_week_total)
        except ZeroDivisionError:
            if diff > 0:
                percent_week = 100
            else:
                percent_week = 0

        weekly_count = []
        for i in range(weeks):
            start = current_week_start - timedelta(weeks=i)
            end = start + timedelta(weeks=1)

            # Total number of activities (per week) for previous weeks
            count = activities.qs.filter(
                report_date__range=[start, end]).count()
            weekly_count.append({'week': weeks - i, 'activities': count})

        kwargs = {
            'total': total,
            'quarter_total': quarter_total,
            'quarter_growth_percentage': percent_quarter * 100,
            'week_total': week_total,
            'week_growth_percentage': percent_week * 100,
            'total_per_week': weekly_count
        }

        kpi = namedtuple('ActivitiesKPI', kwargs.keys())(*kwargs.values())
        serializer = BaseKPISerializer(kpi)

        return Response(serializer.data)
