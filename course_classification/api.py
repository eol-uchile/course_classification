""" search business logic implementations """
# Python Standard Libraries
import datetime
import logging

# Installed packages (via pip)
from django.db.models import Q
from search.api import *

# Edx dependencies
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

# Internal project dependencies
from course_classification.helpers import get_courses_by_classification, set_data_courses


log = logging.getLogger(__name__)  # pylint: disable=invalid-name

def course_discovery_search_eol(search_term=None, size=20, from_=0, order_by="", year="", state="", classification=""):
    """
    Course Discovery activities against the search engine index of course details
    """
    # We'll ignore the course-enrollment information in field and filter
    # dictionary, and use our own logic upon enrollment dates for these
    (search_fields, _, exclude_dictionary) = SearchFilterGenerator.generate_field_filters()
    use_field_dictionary = {}
    searcher = SearchEngine.get_search_engine(getattr(settings, "COURSEWARE_INDEX_NAME", "courseware_index"))
    if not searcher:
        raise NoSearchEngineError("No search engine specified in settings.SEARCH_ENGINE")
    filter_dictionary = {} #"hidden": False
    sort = ""
    year_int = ""
    # Initialize variable to save querys
    query = Q(catalog_visibility="both")
    if order_by == "newer":
        sort = "start:desc"
    if order_by == "older":
        sort = "start"
    # Check if year exist and test if is it numeric
    if year != "" and year.isnumeric():
        year_int = int(year)
        # Check if the start date range between January 1 and December 31 of a year
        query &= Q(start__range = (datetime(year_int, 1, 1), datetime(year_int, 12, 31)))
    # Check if state exist and test if in one of possible states
    if state in ['active', 'finished','coming_soon']:
        if state == 'active':
            # Check if end date is greater than today or null and the start date range is between January 1 and today
            if year_int != "":
                query &= Q(Q(end__gt = datetime.utcnow()) | Q(end__isnull = True)) & Q(start__range = (datetime(year_int, 1, 1), datetime.utcnow()))
            # Check if end date is greater than today or null and start date is less than or equal to today
            else:
                query &= Q(Q(end__gt = datetime.utcnow()) | Q(end__isnull = True)) & Q(start__lte = datetime.utcnow())
        elif state == 'finished':
            # Check if end date is less than today
            query &= Q(end__lte = datetime.utcnow())
        elif state == 'coming_soon':
            # Check if the start date range between today and December 31 of a year
            if year_int != "":
                query &= Q(start__range = (datetime.utcnow(), datetime(year_int, 12, 31)))
            # Check if the start date is greater than today
            else:
                query &= Q(start__gt = datetime.utcnow())
    # Check if classification exist
    if classification != "":
        try:
            courses = get_courses_by_classification(int(classification))
            query &= Q(id__in=courses)
        except Exception as e:
            log.error("Course Discovery - Error in course_classification get_courses_by_classification function, error: {}".format(str(e)))
            pass
    # Check if query is not empty
    if query:
        ids = list(CourseOverview.objects.exclude(query).values("id"))
        ids = [str(x['id']) for x in ids]
        exclude_dictionary["_id"] = ids

    # get results using exclude terms
    results = searcher.search(
        query_string=search_term,
        doc_type="course_info",
        size=size,
        from_=from_,
        field_dictionary=use_field_dictionary,
        filter_dictionary=filter_dictionary,
        exclude_dictionary=exclude_dictionary,
        facet_terms=course_discovery_facets(),
        sort=sort
    )
    try:
        results['results'] = set_data_courses(results['results'])
    except Exception as e:
        log.error("Course Discovery - Error in course_classification set_data_courses function, error: {}".format(str(e)))
        pass
    return results
