---
name: code-reviewing
description: Reviews Python code for security vulnerabilities and potential exploits. Use when auditing code for safety, checking for dangerous functions, or ensuring secure coding practices.
allowed-tools:
  - Read
---
# code-reviewing

## Quick start

Use this skill when reviewing Python code for security vulnerabilities, checking for dangerous functions, or ensuring secure coding practices.

## Core instructions

1. Analyze the Python code for common security vulnerabilities
2. Identify specific security issues with brief comments
3. Suggest secure alternatives or best practices

## Examples

- Input: `def unsafe_function(user_input): return eval(user_input)`
  Output: Security risk: Using eval() on user input can lead to code injection. Consider using ast.literal_eval() instead.

- Input: `import os; os.system('rm -rf /')`
  Output: Security risk: Executing system commands with user input is dangerous. Use subprocess with proper validation instead.

- Input: `exec(user_data)`
  Output: Security risk: exec() allows arbitrary code execution. Use safer alternatives or validate input strictly.

## Common vulnerabilities to check

- `eval()`, `exec()`, `execfile()` - Arbitrary code execution
- `os.system()`, `os.popen()`, `subprocess.call()` without validation - Command injection
- `pickle.loads()` - Unsafe deserialization
- `input()` without validation - Injection attacks
- Hardcoded credentials or secrets
- SQL injection via string formatting
- Path traversal vulnerabilities

## Secure coding practices

- Validate and sanitize all user inputs
- Use parameterized queries for database operations
- Prefer subprocess.run() with list arguments over string commands
- Use safe serialization formats (JSON) over pickle
- Implement proper error handling and logging
- Follow principle of least privilege

## Edge cases

- Handle code with multiple security issues - address each separately
- If code is secure, return "No security vulnerabilities found"
- Preserve original code formatting in feedback
- Consider context when evaluating security - some functions may be safe in controlled environments