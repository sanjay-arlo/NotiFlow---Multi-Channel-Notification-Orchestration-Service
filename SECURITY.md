# Security Policy

## Scope

NotiFlow is a portfolio/prototype project. It has not undergone an independent security audit or production penetration test.

## Reporting a vulnerability

Do not publish sensitive vulnerability details in a public issue. Contact the repository owner privately through the contact information on the GitHub profile and include enough detail to reproduce the issue safely.

## Secrets

Never commit real API keys, passwords, SMTP credentials, Twilio credentials, signing secrets or production connection strings. Use environment variables or a dedicated secret-management system.

## Local testing

Use test accounts and sandbox provider credentials. Do not use real customer data or production credentials in local development.