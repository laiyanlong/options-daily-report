# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly:

1. **DO NOT** open a public GitHub issue
2. Email us at **contact@dappgo.com** with details
3. We will acknowledge receipt within 48 hours
4. We will provide a fix within 7 days for critical issues

## Scope

This project processes financial data for analysis only. It does not:
- Store user credentials or API keys (those are in GitHub Secrets)
- Execute real trades
- Handle personal financial information

## API Keys

- Never commit API keys to the repository
- Use GitHub Secrets for all sensitive configuration
- The `GEMINI_API_KEY` is only used server-side in GitHub Actions
