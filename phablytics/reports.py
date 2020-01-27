# Python Standard Library Imports
import datetime

# Local Imports
from .settings import REVISION_AGE_THRESHOLD_DAYS
from .settings import REVISION_STATUS_REPORT_QUERY_KEY
from .settings import UPCOMING_PROJECT_TASKS_DUE_REPORT_COLUMN_NAMES
from .settings import UPCOMING_PROJECT_TASKS_DUE_REPORT_CUSTOM_EXCLUSIONS
from .settings import UPCOMING_PROJECT_TASKS_DUE_REPORT_EXCLUDED_TASKS
from .settings import UPCOMING_PROJECT_TASKS_DUE_REPORT_ORDER
from .settings import UPCOMING_PROJECT_TASKS_DUE_REPORT_PROJECT_NAME
from .utils import fetch_differential_revisions
from .utils import get_maniphest_tasks_by_project_name
from .utils import get_project_columns_by_project_name
from .utils import get_repos_by_phid
from .utils import get_users_by_phid


def get_report_types():
    """Returns a mapping of report types to classes
    """
    report_types = {
        'RevisionStatus' : RevisionStatusReport,
        'UpcomingProjectTasksDue' : UpcomingProjectTasksDueReport,
    }
    return report_types


class RevisionStatusReport:
    """The Revision Status Report shows a list of Diffs being worked on by a team,
    and outputs them based on their acceptance/needs review status
    """
    def __init__(self):
        self.repo_phids = []
        self.user_phids = []

        self.repos_lookup = None
        self.users_lookup = None

    def _add_users(self, phids):
        self.user_phids.extend(phids)

    def _add_repo(self, phid):
        self.repo_phids.append(phid)

    def _lookup_phids(self):
        """Build lookup tables for User and Repo phids in batch
        """
        self.users_lookup = get_users_by_phid(self.user_phids)
        self.repos_lookup = get_repos_by_phid(self.repo_phids)

    def generate_report(self):
        date_created = (datetime.datetime.now() - datetime.timedelta(days=REVISION_AGE_THRESHOLD_DAYS)).replace(hour=0, minute=0, second=0)
        active_revisions = fetch_differential_revisions(
            REVISION_STATUS_REPORT_QUERY_KEY,
            modified_after_dt=date_created
        )

        revisions_accepted = []
        revisions_todo = []

        for revision in active_revisions:
            if revision.meets_acceptance_criteria:
                revisions_accepted.append(revision)
            elif revision.is_wip:
                # skip WIP
                pass
            else:
                revisions_todo.append(revision)

            self._add_users(revision.reviewer_phids)
            self._add_users([revision.author_phid])

            self._add_repo(revision.repo_phid)

        # generate lookup tables
        self._lookup_phids()

        report = []
        count = 0

        def _format_and_append_revision_to_report(revision, count):
            repo = self.repos_lookup[revision.repo_phid]

            author = self.users_lookup[revision.author_phid]
            acceptors = [f'`{self.users_lookup[phid].name}`' for phid in revision.acceptor_phids]
            blockers = [f'`{self.users_lookup[phid].name}`' for phid in revision.blocker_phids]

            report.append(
                f'{count}. _{revision.title}_ (<{revision.url}|{revision.revision_id}>) by `{author.name}` on `{repo.readable_name}`'
            )
            reviewers_msg = []
            if len(acceptors) > 0:
                reviewers_msg.append(f":white_check_mark: accepted by {', '.join(acceptors)}")
            if len(blockers) > 0:
                if len(reviewers_msg) > 0:
                    reviewers_msg.append('; ')
                else:
                    pass
                reviewers_msg.append(f":no_entry_sign: blocked by {', '.join(blockers)}")

            if len(reviewers_msg) > 0:
                report.append(f"    {''.join(reviewers_msg)}")

            report.append('')

        if len(revisions_accepted) > 0:
            count = 0
            report.append(':white_check_mark: *Accepted and Ready to Land*: _(oldest first)_')
            for revision in sorted(revisions_accepted, key=lambda r: r.modified_ts):
                count += 1
                _format_and_append_revision_to_report(revision, count)
            report.append('')

        if len(revisions_todo) > 0:
            count =0
            if len(revisions_accepted) > 0:
                report.append('')
            else:
                pass

            report.append(':warning: *Needs Review*: _(newest first)_')
            for revision in sorted(revisions_todo, key=lambda r: r.modified_ts, reverse=True):
                count += 1
                _format_and_append_revision_to_report(revision, count)
            report.append('')

        report_string = '\n'.join(report).encode('utf-8').decode('utf-8')
        return report_string


class UpcomingProjectTasksDueReport:
    """The Upcoming Project Tasks Due Report shows a list of tasks ordered by creation date or custom key.
    """
    def __init__(self, columns=None, order=None):
        if order is None:
            order = UPCOMING_PROJECT_TASKS_DUE_REPORT_ORDER

        self.project_name = UPCOMING_PROJECT_TASKS_DUE_REPORT_PROJECT_NAME
        self.columns = UPCOMING_PROJECT_TASKS_DUE_REPORT_COLUMN_NAMES

        #self.project = project
        #self.columns = columns
        self.order = order

    def generate_report(self):
        if self.columns:
            columns = get_project_columns_by_project_name(self.project_name, self.columns)
            column_phids = [
                column.phid
                for column
                in columns
            ]
        else:
            column_phids = []

        maniphest_tasks = get_maniphest_tasks_by_project_name(
            self.project_name,
            column_phids=column_phids,
            order=self.order,
        )

        def _should_include(task):
            #import json
            #print(json.dumps(task.raw_data))
            should_include = (
                task.id_ not in UPCOMING_PROJECT_TASKS_DUE_REPORT_EXCLUDED_TASKS
                and not any([
                    custom_exclusion(task)
                    for custom_exclusion
                    in UPCOMING_PROJECT_TASKS_DUE_REPORT_CUSTOM_EXCLUSIONS
                ])
            )
            return should_include

        tasks = filter(_should_include, maniphest_tasks)

        report = []
        count = 0

        report.append(f"*{self.project_name} - {', '.join(self.columns)} - Tasks Due Soon*")

        for task in tasks:
            count += 1
            report.append(f'{count}. _{task.name}_ (<{task.url}|{task.task_id}>)')

        report_string = '\n'.join(report).encode('utf-8').decode('utf-8')
        return report_string
