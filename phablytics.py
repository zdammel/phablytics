# Python Standard Library Imports
import argparse
import pprint

from htk import slack_message
from phablytics.reports import get_report_types
from phablytics.utils import adhoc
from phablytics.utils import whoami


class PhablyticsCLI:
    def __init__(self):
        self.report_types = get_report_types()

    def execute(self):
        self.parse_args()

        if self.test:
            pass
        elif self.adhoc:
            response = adhoc(self.adhoc, method_args=self.adhoc_args)
            pprint.pprint(response)
        elif self.whoami:
            user = whoami()
            pprint.pprint(user.raw_data)
        elif self.report_type:
            report_class = self.report_types.get(self.report_type)
            if report_class:
                report = report_class().generate_report()
                if self.slack:
                    slack_channel = self.slack_channel
                    slack_message(text=report, channel=slack_channel)
                else:
                    print(report)

    def parse_args(self):
        arg_parser = argparse.ArgumentParser(description='Phablytics report generator.')
        report_type_choices = sorted(self.report_types.keys())
        arg_parser.add_argument(
            '-r', '--report_type',
            help=f"Report type.",
            choices=report_type_choices,
            required=False
        )
        arg_parser.add_argument(
            '--slack',
            action='store_true',
            help='Output report to Slack.',
            required=False
        )
        arg_parser.add_argument(
            '--slack-channel',
            help='Slack channel to use for displaying report.',
            required=False
        )
        arg_parser.add_argument(
            '-t', '--test',
            action='store_true',
            help='Test. Development use only.',
            required=False
        )
        arg_parser.add_argument(
            '-a', '--adhoc',
            help='Runs an adhoc Conduit method.',
            required=False
        )
        arg_parser.add_argument(
            '--adhoc-args',
            help='Specifies arguments for Conduit method, used with --adhoc.',
            required=False
        )
        arg_parser.add_argument(
            '-w', '--whoami',
            action='store_true',
            help='Runs whoami.',
            required=False
        )

        cli_args = arg_parser.parse_args(namespace=self)
        self.arg_parser = arg_parser


def main():
    PhablyticsCLI().execute()


if __name__ == '__main__':
    main()
