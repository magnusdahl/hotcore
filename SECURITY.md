# Security Policy

## Supported Versions

The hotcore project currently supports the latest released version published to PyPI. Security fixes are applied to the `main` branch and released as patch versions when necessary.

| Version | Supported |
|---------|-----------|
| 1.x     | ✅        |

## Reporting a Vulnerability

If you discover a security vulnerability, **do not** open a public issue. Instead, please email [security@consistis.com](mailto:security@consistis.com) with the following information:

- Description of the vulnerability and potential impact
- Steps to reproduce or proof-of-concept exploit, if available
- Affected versions of hotcore (if known)
- Your contact information for follow-up questions

We aim to acknowledge vulnerability reports within **2 business days** and provide an estimated timeline for remediation within **7 business days**. Once a fix is ready, we will coordinate a disclosure timeline with you before releasing publicly.

## Security Best Practices

- Always run tests with a clean Redis database; the test suite flushes data automatically but double-check your configuration when using a shared instance.
- Use TLS/SSL when connecting to Redis in production. The `RedisConnectionManager` now accepts an `ssl.SSLContext` and explicit `connection_kwargs` for fine-grained certificate verification.
- Consider enabling Redis authentication and network-level protections (firewalls, VPNs, security groups) when deploying.

Thank you for helping keep the project and its users safe!
