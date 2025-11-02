# Security Policy

## Supported Versions

The following versions of SDCvalidator are currently supported with security updates:

| Version | Supported          | Notes |
| ------- | ------------------ | ----- |
| 4.0.x   | :white_check_mark: | Current release |
| < 4.0   | :x:                | Legacy versions - no longer supported |

---

## What Qualifies as a Security Vulnerability?

For SDCvalidator (an XML validation library), security vulnerabilities may include:

### XML Processing Vulnerabilities

- **XML External Entity (XXE) injection** - Malicious external entity references
- **XML Entity Expansion (Billion Laughs)** - Resource exhaustion attacks
- **XPath injection** - Malicious XPath expressions
- **DTD processing** - Dangerous DTD loading from untrusted sources

### Code Execution Vulnerabilities

- **Arbitrary code execution** - Remote code execution through validation
- **Path traversal** - File system access outside intended directories
- **Command injection** - OS command execution through user input
- **Unsafe deserialization** - Dangerous pickle/eval usage

### Resource Exhaustion

- **Denial of Service (DoS)** - Resource exhaustion through crafted input
- **Memory exhaustion** - Unbounded memory consumption
- **CPU exhaustion** - Infinite loops or exponential processing
- **Disk exhaustion** - Unbounded file writing

### Dependency Vulnerabilities

- **Known CVEs** in dependencies (elementpath, etc.)
- **Supply chain attacks** - Compromised dependencies
- **Outdated dependencies** with known vulnerabilities

---

## What is NOT a Security Vulnerability

The following are **not** security vulnerabilities:

- **Validation bypass** (unless it enables attacks) - Incorrect validation is a bug, not a security issue
- **Performance issues** - Unless they enable DoS attacks
- **Documentation errors** - Unless they lead users to insecure practices
- **Feature requests** - Use normal issue tracker
- **Compatibility issues** - Not security-related

---

## Reporting a Vulnerability

**Please DO NOT report security vulnerabilities through public GitHub issues.**

### Private Reporting

To report a security vulnerability:

1. **Email**: Send details to `security@axius-sdc.com`
   - Subject: `[SECURITY] SDCvalidator: Brief description`
   - Include: Detailed description, reproduction steps, impact assessment

2. **GitHub Security Advisory**: Use GitHub's private vulnerability reporting
   - Go to repository → Security tab → Report a vulnerability
   - Fill out the form with details

### What to Include

Please provide:

- **Description** - What is the vulnerability?
- **Impact** - What could an attacker do?
- **Reproduction** - Step-by-step instructions to reproduce
- **Affected versions** - Which versions are vulnerable?
- **Environment** - Python version, OS, dependencies
- **Suggested fix** - If you have ideas (optional)
- **Your contact info** - For follow-up questions

### What to Expect

1. **Acknowledgment** - Within 48 hours
2. **Initial assessment** - Within 1 week
3. **Regular updates** - Every week until resolved
4. **Fix timeline** - Typically 30 days for critical issues
5. **Disclosure** - Coordinated with you (typically 90 days)

---

## Security Best Practices for Users

### When Validating Untrusted XML

```python
from sdcvalidator import SDC4Validator

# ✅ SAFE: Disable external entity resolution
validator = SDC4Validator('schema.xsd')
validator.schema.use_fallback = False  # Disable network access

# Validate with resource limits
recovered = validator.validate_with_recovery(
    'untrusted.xml',
    max_depth=100,  # Limit recursion depth
    timeout=30  # Timeout after 30 seconds
)
```

### Avoid These Patterns

```python
# ❌ UNSAFE: Loading schemas from user input
user_schema_url = request.GET['schema']  # User-controlled
validator = SDC4Validator(user_schema_url)  # DON'T DO THIS

# ✅ SAFE: Whitelist schemas
ALLOWED_SCHEMAS = {
    'patient': '/path/to/patient_schema.xsd',
    'product': '/path/to/product_schema.xsd'
}
schema_path = ALLOWED_SCHEMAS.get(user_choice)
if schema_path:
    validator = SDC4Validator(schema_path)
```

```python
# ❌ UNSAFE: Unrestricted file writing
output_path = user_input  # User-controlled path
validator.save_recovered_xml(output_path, instance)  # Path traversal risk

# ✅ SAFE: Validate and restrict paths
from pathlib import Path

def safe_output_path(user_input: str, base_dir: Path) -> Path:
    """Ensure output path is within allowed directory."""
    output = (base_dir / user_input).resolve()
    if not output.is_relative_to(base_dir):
        raise ValueError("Invalid output path")
    return output

safe_path = safe_output_path(user_input, Path('/allowed/output/dir'))
validator.save_recovered_xml(str(safe_path), instance)
```

### Resource Limits

```python
import resource
import signal

# Set memory limit (Linux/Unix)
resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, -1))  # 512MB

# Set timeout
def timeout_handler(signum, frame):
    raise TimeoutError("Validation timed out")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)  # 30 second timeout

try:
    result = validator.validate_with_recovery('untrusted.xml')
finally:
    signal.alarm(0)  # Cancel alarm
```

---

## Known Security Considerations

### XML External Entity (XXE) Protection

**Status**: ✅ Protected by default

SDCvalidator uses Python's `xml.etree.ElementTree` with safe defaults:
- External entities disabled by default
- DTD processing restricted
- Network access disabled

**Additional protection**:
```python
# Explicitly disable external entity resolution
from sdcvalidator import SDC4Validator

validator = SDC4Validator('schema.xsd')
validator.schema.use_fallback = False
```

### Resource Exhaustion Protection

**Status**: ⚠️ Partial protection

SDCvalidator has some built-in limits:
- Maximum recursion depth (configurable)
- Element limits (configurable)

**Recommended**: Set additional limits in production:
```python
from sdcvalidator import SDC4Validator, limits

# Configure limits
limits.MAX_XML_DEPTH = 100
limits.MAX_MODEL_DEPTH = 50

validator = SDC4Validator('schema.xsd')
```

### XPath Injection Protection

**Status**: ✅ Protected

XPath expressions in SDCvalidator:
- Use parameterized queries where possible
- Validate XPath expressions before execution
- Use elementpath library which sanitizes inputs

**User responsibility**: Don't construct XPath from untrusted input:
```python
# ❌ UNSAFE
user_xpath = request.GET['xpath']
elements = tree.findall(user_xpath)  # XPath injection

# ✅ SAFE
# Use predefined, safe XPath expressions
SAFE_XPATHS = {
    'patients': './/Patient',
    'products': './/Product'
}
xpath = SAFE_XPATHS.get(user_choice, './/default')
elements = tree.findall(xpath)
```

---

## Dependency Security

### Dependency Monitoring

We monitor dependencies for known vulnerabilities:

- **Dependabot** - Automated security updates
- **GitHub Security Advisories** - Vulnerability notifications
- **Regular audits** - Manual security reviews

### Core Dependencies

- **elementpath** (>=5.0.1) - XPath evaluation
  - Actively maintained
  - Security issues addressed promptly

### Updating Dependencies

```bash
# Check for security updates
pip list --outdated

# Update dependencies
pip install --upgrade elementpath

# Run tests after update
pytest tests/ -v
```

---

## Security Update Process

### For PATCH Versions (Security Fixes)

Critical security fixes released as PATCH versions:

1. **Private fix development** - Vulnerability fixed privately
2. **Testing** - Comprehensive testing of fix
3. **Version bump** - e.g., 4.0.1 → 4.0.2
4. **Security advisory** - Published on GitHub
5. **PyPI release** - Updated package published
6. **User notification** - Announcement via GitHub and email
7. **Public disclosure** - CVE assigned if applicable

### Timeline

- **Critical vulnerabilities**: 1-7 days
- **High severity**: 7-14 days
- **Medium severity**: 14-30 days
- **Low severity**: Included in next regular release

---

## Vulnerability Disclosure Policy

### Our Commitments

1. **Acknowledgment** - Respond within 48 hours
2. **Communication** - Regular updates throughout process
3. **Credit** - Recognize reporters (if desired)
4. **Transparency** - Public disclosure after fix
5. **Coordination** - Work with reporter on timing

### Timeline

1. **Day 0**: Vulnerability reported
2. **Day 2**: Acknowledgment sent
3. **Day 7**: Initial assessment complete
4. **Day 30**: Fix developed and tested (target)
5. **Day 90**: Public disclosure (default, adjustable)

### Exceptions to Timeline

- **Active exploitation** - May accelerate disclosure
- **Trivial fixes** - May be faster
- **Complex issues** - May need more time
- **Reporter request** - We'll work with you

---

## Security Hall of Fame

We recognize security researchers who responsibly disclose vulnerabilities:

*None yet - be the first!*

---

## Security Features

### Built-In Protections

✅ **XXE Protection** - External entities disabled
✅ **Safe XML Parsing** - Using stdlib ElementTree with safe defaults
✅ **XPath Safety** - Parameterized queries, input validation
✅ **Resource Limits** - Configurable depth and element limits
✅ **No eval()** - No dynamic code execution
✅ **Path validation** - File operations validated

### User-Configurable Protections

- **Timeout limits** - Set maximum validation time
- **Memory limits** - OS-level resource constraints
- **Recursion limits** - Maximum XML depth
- **Network isolation** - Disable external resource loading

---

## Security Testing

### Automated Testing

- **Static analysis** - MyPy type checking, Flake8 linting
- **Dependency scanning** - Dependabot alerts
- **CI/CD security** - GitHub Actions security scanning

### Manual Testing

- **Code review** - All PRs reviewed for security
- **Penetration testing** - Periodic security audits
- **Fuzzing** - Testing with malformed input (planned)

---

## Contact

For security issues: `security@axius-sdc.com`

For non-security issues:
- **GitHub Issues** - https://github.com/Axius-SDC/sdcvalidator/issues
- **Email** - contact@axius-sdc.com

---

## Additional Resources

- [OWASP XML Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/XML_Security_Cheat_Sheet.html)
- [Python XML Processing Security](https://docs.python.org/3/library/xml.html#xml-vulnerabilities)
- [CWE-611: XXE](https://cwe.mitre.org/data/definitions/611.html)
- [NIST National Vulnerability Database](https://nvd.nist.gov/)

---

**Security is a shared responsibility. Thank you for helping keep SDCvalidator secure!**
