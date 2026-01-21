# Python Standard Libraries
import logging

# Installed packages (via pip)
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

# Edx dependencies
from lms.djangoapps.course_info.models import MainClassification, CourseClassification as InitialCourseClassification

# Internal project dependencies
from course_classification.models import CourseCategory, CourseClassification

logger = logging.getLogger(__name__)

def import_course_classification( dry_run=True ):
    """
    Import CourseClassification objects from course_info app to CourseClassification in course_classification
    """
    # Obtain original data CourseClassification
    old_course_classification = InitialCourseClassification.objects.all()
    all_current_course_classification = CourseClassification.objects.values_list("course_id", flat=True)
    current_course_category = 0
    new_course_classifications = []

    # Iteration to save new course_classification data
    for cc in old_course_classification:
        if not( cc.course_id in all_current_course_classification ):
            course_classification = CourseClassification(course_id = cc.course_id)
            course_classification.full_clean()
            new_course_classifications.append(course_classification)
        else:
            current_course_category += 1
    try:
        with transaction.atomic():
            CourseClassification.objects.bulk_create(new_course_classifications, ignore_conflicts=True)

            for cc in old_course_classification:
                course_classification = CourseClassification.objects.get(
                        course_id = cc.course_id
                    )
                category = CourseCategory.objects.get(name=cc.MainClass.name)
                course_classification.course_category.add(category)
            if  dry_run:
                transaction.set_rollback(True)
            return len(old_course_classification), current_course_category, len(new_course_classifications)
    except Exception as e:
        logger.error(f'Exception happens: {e}')
        # Raise exception
        raise Exception(f"Error while copying categories {e} from import_course_classification function")

def import_categories( dry_run=True ):
    """
    Import MainClassification objects from course_info app to CourseCategory in course_classification
    """
    # Obtain original data MainClassification
    old_categories = MainClassification.objects.all()
    all_current_categories = CourseCategory.objects.values_list("name", flat=True)
    current_categories = 0
    new_categories = []

    # Iterate to save new categories
    for cat in old_categories:
        # Check if category name already exist
        if not(cat.name in all_current_categories):
            category = CourseCategory(
                name = cat.name,
                sequence = cat.sequence,
                show_opt = cat.show_opt
            )
            category.full_clean()
            new_categories.append(category)
        else:
            current_categories += 1
    try:
        with transaction.atomic():
            CourseCategory.objects.bulk_create(new_categories, ignore_conflicts=True)
            if  dry_run:
                transaction.set_rollback(True)
        return len(old_categories), current_categories, len(new_categories)
    except Exception as e:
        logger.error(f'Exception happens: {e}')
        # Raise exception
        raise Exception(f"Error while copying categories {e} from import_categories function")

class Command(BaseCommand):
    help = """
        The course classification was decoupled from the previous model in Platform ( course_info.MainClassification ) and mapped to the current model used in 
        this application (course_classification.CourseCategory ), with the sole purpose of migrating the historical classification data. This command does not introduce new functionality 
        or modify existing business logic; it is strictly limited to transferring and mapping the existing information.
        """ 
    def add_arguments(self, parser):
        parser.add_argument('--dry_run', action='store_true')

    def handle(self, *args, **options):
        # Check if course_info is installed
        if not(apps.is_installed('lms.djangoapps.course_info')) or not(apps.is_installed('course_classification')):
            self.stdout.write(
                self.style.ERROR(
                    f"One of the apps, course_info or course_classification, isn't installed, so I can't continue with the commands."
                )
            )
            logger.error(f"One of the apps, course_info or course_classification, isn't installed, so I can't continue with the commands.")
            raise

        dry_run = options['dry_run']
        
        try:
            import_result = import_categories( dry_run )
            if  dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"""
                            This is a dry_run
                            A total of {import_result[0]} objects were found.
                            A total of {import_result[1]} objects already exist in CourseCategory model.
                            A total of {import_result[2]} objects could be copied to the CourseCategory model.
                        """
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"""
                            A total of {import_result[0]} objects were found.
                            A total of {import_result[1]} objects already exist in CourseCategory model.
                            A total of {import_result[2]} objects have been copied to CourseCategory model
                        """
                    )
                )
        except Exception as e:
            logger.error(f'Exception happens: {e}')
            # Raise exception
            raise Exception(f"Error while copying categories {e}")
        
        try:
            import_result = import_course_classification( dry_run)
            if  dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"""
                            This is a dry_run
                            A total of {import_result[0]} objects were found.
                            A total of {import_result[1]} objects already exist in CourseClassification model.
                            A total of {import_result[2]} objects could be copied to the CourseClassification model.
                        """
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"""
                            A total of {import_result[0]} objects were found.
                            A total of {import_result[1]} objects already exist in CourseClassification model.
                            A total of {import_result[2]} objects have been copied to the CourseClassification model.
                        """
                    )
                )
        except Exception as e:
            logger.error(f'Exception happens: {e}')
            # Raise exception
            raise Exception(f"Error while copying course_classification {e}")
