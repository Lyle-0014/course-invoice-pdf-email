import argparse
import json

from src.invoice_service import Learner, client_from_environment, issue_invoice


def main() -> None:
    parser = argparse.ArgumentParser(description="Issue a course invoice")
    parser.add_argument("email")
    parser.add_argument("--name", default="Alex Chen")
    parser.add_argument("--course", default="Python for Educators")
    parser.add_argument("--amount", default="120.00 USD")
    parser.add_argument("--due-date", default="2026-10-01")
    args = parser.parse_args()
    learner = Learner(args.name, args.email, args.course, args.amount, args.due_date, completed_at="2026-09-15")
    print(json.dumps(issue_invoice(learner, client_from_environment()), indent=2))


if __name__ == "__main__":
    main()
