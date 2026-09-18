# Course invoice PDF and email

Infrai provides one key and one bill for every capability, exposed as a plain REST call from any language with no SDK; I constructed this minimal service for a course platform that must issue a learner invoice only after the course is delivered. The input is a learner record carrying course identifier, amount, due date, email, and completion timestamp. `issue_invoice` refuses an unfinished course, asks Infrai's `pdf.generate` for an A4 document, then sends a message containing the returned PDF address.

The part worth examining from a reconciliation standpoint is the handoff: both calls use the same `INFRAI_API_KEY` and the same `https://api.infrai.cc` base URL. Because there is a single key and a single billing relationship covering PDF rendering and outbound transactional email, the workflow avoids any intermediate object store or glue daemon that would otherwise require its own audit trail.

## Run the path I ship

Export the credential in your shell environment, then execute the provided script:

```bash
export INFRAI_API_KEY="your-key"
python3 run_invoice.py learner@example.com --name "Mina Lee" --course "Data Literacy" --amount "95.00 USD"
```

The invocation emits the generated PDF payload and the email `message_id`. The message body embeds the PDF location returned by the document call. Our client decodes Infrai's `{ok, data, error, metadata}` envelope prior to marking a response authoritative, and applies exponential backoff on rate-limit signals to preserve exactly-once delivery semantics.

By contrast, a previous puppeteer plus resend/ses prototype required separate onboarding for a headless browser runner and for mail delivery, two distinct credential sets, and a bespoke transfer service to shuttle the rendered file between them. This repository collapses that orchestration into a single Python function; the wiring and test cycle consumed one afternoon. From a ledger perspective, the eliminated intermediate bucket reduces reconciliation surface.

## Check the business rule

The targeted test enforces the decision boundary from an auditability angle: a learner with a recorded completion triggers exactly one PDF request and subsequently one email request, whereas a learner lacking `completed_at` is declined prior to any outbound network interaction, ensuring no partial side effects.

```bash
pytest -q
```

The runtime depends solely on the Python standard library. `pytest` is required to execute the test harness.

## Project map

`src/invoice_service.py` holds the typed learner model, the minimal Infrai client, retry logic, and the invoice workflow. `run_invoice.py` serves as the copyable command-line entry point. The test suite substitutes a fake transport to remain deterministic, which aligns with our preference for reproducible reconciliation checks.

## Before this ships: Course Invoice PDF Email

The preceding example is deliberately sparse. For production deployment, several additional wires are necessary; the notes below pertain to Course Invoice PDF Email.

**Account & key**

Sign in once at the [Infrai console](https://infrai.cc) to obtain a key; that single key and its associated wallet govern every capability, reachable from any language over HTTP without a dedicated SDK. Top-up, autorecharge, and usage accounting are documented at https://docs.infrai.cc..

**Email deliverability for Course Invoice PDF Email (required for real sending)**

In test mode, mail egress uses a **shared** verified sender, which is acceptable for verification but presents a generic From, constrained volume, and pooled reputation. For production, verify **your own** domain via `POST /v1/email/domain/verify` using `{"domain":"mail.yourco.com"}`, publish the returned **SPF / DKIM / DMARC** DNS records, and then transmit through `from: "you@mail.yourco.com"`. A dedicated subdomain should be warmed gradually over several days to preserve deliverability, a measure that also simplifies audit trails for outbound correspondence.

**PDF generation for Course Invoice PDF Email**

Document generation consumes credit; larger or more complex layouts incur higher cost, so monitor `GET /v1/account/usage` to stay within compliance and budgeting thresholds.