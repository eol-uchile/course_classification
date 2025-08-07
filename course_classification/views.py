#!/usr/bin/env python
# -- coding: utf-8 --

# Python Standard Libraries
import json
import logging

# Installed packages (via pip)
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.test.client import RequestFactory
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST
from django.views.generic.base import View
from eventtracking import tracker as track
from search.views import _process_pagination_values
import six

# Edx dependencies
from common.djangoapps.util.json_request import JsonResponse

# Internal project dependencies
from .api import *
from .models import MainCourseClassification, MainCourseClassificationTemplate

logger = logging.getLogger(__name__)
   
class CourseClassificationView(View):
    """
        Page view for institutions (MainCourseClassification)
    """
    def get(self, request, org_id):
        lang_options = ['en', 'es_419']
        try:
            lang = request.COOKIES.get('openedx-language-preference', 'en')
            if lang == "es-419":
                lang = "es_419"
            if lang not in lang_options:
                lang = 'en'
            lang_options.remove(lang)
            classification = MainCourseClassification.objects.get(id=org_id, is_active=True)
            if classification.banner == "":
                logger.info("CourseClassificationView - Classification dont have banner, MainCourseClassification id: {}".format(org_id))
                return HttpResponseRedirect('/')
            if MainCourseClassificationTemplate.objects.filter(main_classification=classification, language=lang).exists():
                template = MainCourseClassificationTemplate.objects.get(main_classification=classification, language=lang)
            elif MainCourseClassificationTemplate.objects.filter(main_classification=classification, language=lang_options[0]).exists():
                template = MainCourseClassificationTemplate.objects.get(main_classification=classification, language=lang_options[0])
            else:
                logger.info("CourseClassificationView - Classification dont have es_419 or en template, MainCourseClassification id: {}".format(org_id))
                return HttpResponseRedirect('/')
            # Recreate https request
            factory = RequestFactory()
            data = {
                'search_string': '',
                'order_by': '',
                'year': '',
                'state': '',
                'classification': org_id,
                'page_size': '20',
                'page_index': '0'
            }
            # Request call using data parameters
            request = factory.post('/course_classification/search/', data=data)
            response = course_discovery_eol(request)
            results = json.loads(response.content)
            # Get courses from results
            courses = results["results"]
            context = {
                'institution_name': classification.name,
                'institution_banner': classification.banner.url,
                'institution_html': template.template,
                'courses': courses
            }
            return render(request, 'course_classification/institution.html', context)
        except Exception as e:
            logger.info("CourseClassificationView - Active classification does not exists, id: {}, error: {}".format(org_id, str(e)))
            return HttpResponseRedirect('/')

@require_POST
def course_discovery_eol(request):
    """
    Search for courses

    Args:
        request (required) - django request object

    Returns:
        http json response with the following fields
            "took" - how many seconds the operation took
            "total" - how many results were found
            "max_score" - maximum score from these resutls
            "results" - json array of result documents

            or

            "error" - displayable information about an error that occured on the server

    POST Params:
        "search_string" (optional) - text with which to search for courses
        "page_size" (optional)- how many results to return per page (defaults to 20, with maximum cutoff at 100)
        "page_index" (optional) - for which page (zero-indexed) to include results (defaults to 0)
    """
    results = {
        "error": _("Nothing to search")
    }
    status_code = 500

    search_term = request.POST.get("search_string", None)
    order_by = request.POST.get("order_by", "")
    year = request.POST.get("year", "")
    state = request.POST.get("state", "")
    cc = request.POST.get("classification", "")
    featured = bool(request.POST.get("featured", False))

    try:
        size, from_, page = _process_pagination_values(request)

        # Analytics - log search request
        track.emit(
            'edx.course_discovery.search.initiated',
            {
                "search_term": search_term,
                "page_size": size,
                "page_number": page,
            }
        )

        results = course_discovery_search_eol(
            search_term=search_term,
            size=size,
            from_=from_,
            order_by=order_by,
            year=year,
            state=state,
            classification=cc,
            featured= featured
        )

        # Analytics - log search results before sending to browser
        track.emit(
            'edx.course_discovery.search.results_displayed',
            {
                "search_term": search_term,
                "page_size": size,
                "page_number": page,
                "results_count": results["total"],
            }
        )

        status_code = 200

    except ValueError as invalid_err:
        results = {
            "error": six.text_type(invalid_err)
        }
        logger.debug(six.text_type(invalid_err))

    except QueryParseError:
        results = {
            "error": _('Your query seems malformed. Check for unmatched quotes.')
        }

    # Allow for broad exceptions here - this is an entry point from external reference
    except Exception as err:  # pylint: disable=broad-except
        results = {
            "error": _('An error occurred when searching for "{search_string} {err}"').format(search_string=search_term, err=err)  # lint-amnesty, pylint: disable=unicode-format-string
        }
        logger.exception(
            'Search view exception when searching for %s for user %s: %r',  # lint-amnesty, pylint: disable=unicode-format-string
            search_term,
            request.user.id,
            err
        )

    return JsonResponse(results, status=status_code)
