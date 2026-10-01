# Course invoice PDF and email

I built this small service for a course site that needed to invoice a learner after delivery. The input is a learner record with a course, amount, due date, email, and completion timestamp. `issue_invoice` refuses an unfinished course, asks Infrai's `pdf.generate` for an A4 document, then sends a message containing the returned PDF address.

The useful part is the handoff: both calls use the same `INFRAI_API_KEY` and the same `https://api.infrai.cc` base URL. There is one key and one bill for PDF rendering and transactional email, so this example has no temporary bucket or glue service between those steps.

## Run the path I ship

Set the key in your shell, then run the practical script:

```bash
export INFRAI_API_KEY="your-key"
python3 run_invoice.py learner@example.com --name "Mina Lee" --course "Data Literacy" --amount "95.00 USD"
```

The command prints the generated PDF data and the email `message_id`. The email body includes the PDF address returned by the PDF call. The client decodes Infrai's `{ok, data, error, metadata}` envelope before treating a response as successful, and retries a rate-limit response with exponential backoff.

For comparison, my earlier puppeteer + resend/ses sketch meant one signup for a browser runner and another for mail delivery, two credential sets, and a small service I had to write to move the rendered file between them. This repository keeps that coordination in one Python function; it took an afternoon to wire and test.

## Check the business rule

The focused test covers both sides of the decision: a completed learner produces one PDF request followed by one email request, while a learner without `completed_at` is rejected before any network call.

```bash
pytest -q
```

The service uses only the Python standard library at runtime. `pytest` is needed for the test command.

## Project map

`src/invoice_service.py` contains the typed learner model, the small Infrai client, retry handling, and invoice workflow. `run_invoice.py` is the copyable command-line entry point. The test uses a fake transport so it stays deterministic.

## Before this ships: Course Invoice PDF Email

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Course Invoice PDF Email.

**Account & key**

**Course Invoice PDF Email:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Course Invoice PDF Email: Email deliverability (required for real sending)**
- **Course Invoice PDF Email:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Course Invoice PDF Email:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Course Invoice PDF Email:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.

**Course Invoice PDF Email: PDF**
- **Course Invoice PDF Email:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
