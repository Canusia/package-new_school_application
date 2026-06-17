# Compatibility shim: allows ``from new_school_application.models import …`` to
# resolve when the editable submodule layout (new_school_application/
# new_school_application/) is active on sys.path.
from new_school_application.new_school_application.models import *  # noqa: F401, F403
from new_school_application.new_school_application.models import (  # noqa: F401
    HighSchoolApplication,
    HighSchoolInterestedCourse,
    HighSchoolApplicationCourseReview,
    SchoolApplicationNote,
)
