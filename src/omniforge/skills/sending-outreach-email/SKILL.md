---
name: sending-outreach-email
description: Sends outreach emails to potential clients or contacts using provided email details including recipient, subject, body, and attachments. Use when reaching out to new prospects or following up with existing contacts.
allowed-tools: "Read,Write"
---
# sending-outreach-email

## Quick start

Use this skill when you have email details ready and need to send an outreach message. Collect recipient, subject, body, and attachments, then follow the workflow steps to send the email.

## Core workflow

Copy this checklist and track your progress:

```
Email Sending Progress:
- [ ] Step 1: Collect email details from user
- [ ] Step 2: Determine email type and adapt content
- [ ] Step 3: Attempt to send email through configured service
- [ ] Step 4: Retry up to 3 times if email fails (exponential backoff)
- [ ] Step 5: Log error and notify user if all retries fail
```

### Step 1: Collect email details

Use the `Read` tool to gather email details from user input:
- Recipient email address
- Subject line
- Email body content
- Attachments (if any)

### Step 2: Determine email type and adapt content

Analyze the subject and body to determine if this is:
- Cold outreach: First contact with new prospect
- Follow-up: Existing contact after previous conversation

Adapt tone and content accordingly:
- Cold outreach: More formal, value-focused introduction
- Follow-up: Reference previous conversation, maintain continuity

### Step 3: Attempt to send email through configured service

Use the configured email service to send the email. For detailed email service configuration, read {{baseDir}}/references/email-service-setup.md.

### Step 4: Retry up to 3 times if email fails

If email sending fails:
- Wait 2 seconds before first retry
- Wait 4 seconds before second retry  
- Wait 8 seconds before third retry
- Use exponential backoff strategy

### Step 5: Log error and notify user if all retries fail

If all 3 retries fail:
- Log detailed error information
- Notify user of failure with error details
- Suggest checking recipient address and email service status

## Examples

- Input: recipient@example.com, subject: "Partnership Opportunity", body: "Dear [Name], I'd like to discuss a potential partnership...", attachments: "company_brochure.pdf"
  Output: Email sent successfully to recipient@example.com

- Input: prospect@company.com, subject: 'Following up on our conversation', body: 'Hi [Name], I wanted to follow up on our discussion from last week...', attachments: ''
  Output: Email sent successfully to prospect@company.com

## Edge cases

- If recipient email is invalid, log error and notify user immediately
- If attachments are specified but file doesn't exist, skip attachments and proceed
- If email body is empty, log error and abort sending
- Handle rate limiting by increasing backoff time between retries
- If email service is temporarily unavailable, retry with maximum backoff time

## Validation

After completing all steps:
1. Verify email was sent successfully or failure was properly logged
2. Check that attachments (if any) were properly processed
3. Confirm user was notified of outcome
4. Review error logs if sending failed