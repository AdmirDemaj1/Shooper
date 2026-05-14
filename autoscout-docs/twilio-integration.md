# Twilio WhatsApp Integration

**Status:** Current development approach for AutoScout AI

AutoScout AI uses **Twilio** for WhatsApp messaging during development and testing. Twilio provides rapid iteration, lower costs, and reliable delivery without the overhead of Meta Business Manager verification.

## Why Twilio?

- ✅ **No verification delays** — instant setup, unlike Meta's 2–4 week business verification
- ✅ **Predictable pricing** — flat per-message cost with no quality rating penalties
- ✅ **Testing-friendly** — sandbox mode for development without real WhatsApp delivery
- ✅ **Provider-agnostic interface** — easy migration to Meta Cloud API in production

## Setup

### Prerequisites

1. [Create a Twilio account](https://www.twilio.com/console)
2. Verify your phone number (for testing)
3. Enable WhatsApp integration in the Twilio console

### Twilio Console Setup

1. Go to **Messaging > Try it out > Send a WhatsApp message**
2. Create a WhatsApp Sandbox:
   - You'll be given a sandbox number (e.g., `+1 415 523 8886`)
   - Send `join <phrase>` to that number from your phone to opt in
3. Copy your:
   - Account SID: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - Auth Token: `your_token_here` (kept secret)
   - WhatsApp phone number (the sandbox number or a production-approved number)

### Backend Configuration

Add to `.env`:

```env
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=your_token_here
TWILIO_WHATSAPP_PHONE_NUMBER=+1415523XXXX
```

### Backend Integration

```python
# autoscout/notifications/twilio_provider.py

from twilio.rest import Client
from pydantic import BaseModel

class TwilioWhatsAppProvider:
    def __init__(self, account_sid: str, auth_token: str, phone_number: str):
        self.client = Client(account_sid, auth_token)
        self.phone_number = phone_number
    
    async def send_template(
        self, 
        to: str,  # E.164 format, e.g. +355 69 123 4567
        template_name: str,
        variables: dict[str, str]
    ) -> dict:
        """Send a WhatsApp template message via Twilio."""
        message = self.client.messages.create(
            from_=f"whatsapp:{self.phone_number}",
            to=f"whatsapp:{to}",
            template={
                "name": template_name,
                "language": {"policy": "en", "code": "en"},
                "variables": list(variables.values()),
            },
        )
        return {"provider_message_id": message.sid, "status": message.status}
    
    async def send_text(self, to: str, body: str) -> dict:
        """Send a plain text message (useful for testing)."""
        message = self.client.messages.create(
            from_=f"whatsapp:{self.phone_number}",
            to=f"whatsapp:{to}",
            body=body,
        )
        return {"provider_message_id": message.sid, "status": message.status}
```

## Template Management

Templates are managed in the **Twilio Console > Messaging > Content Templates**.

### Creating a Template

Example: `autoscout_daily_digest`

```
Hi {{1}}, here are today's top {{2}} matches for your search "{{3}}":

{{4}}

Reply STOP to stop receiving these messages.
```

**Note:** Twilio templates use `{{1}}`, `{{2}}` placeholders (1-indexed), unlike Meta's `{{variable_name}}` style.

### Message Sending Example

```python
await provider.send_template(
    to="+35569123456",
    template_name="autoscout_daily_digest",
    variables={
        "1": "Adi",                          # User name
        "2": "5",                            # Number of matches
        "3": "Honda Civic under €10k",       # Search name
        "4": "• 2019 Civic — €9,500 — 145k km\n• 2018 Civic — €8,900 — 167k km\n...",
    }
)
```

## Handling Inbound Messages

Set up a webhook in the Twilio console to receive inbound WhatsApp replies:

**Webhook URL:** `https://api.autoscout.al/webhooks/twilio`

```python
# autoscout/webhooks/twilio.py

from fastapi import Request

@app.post("/webhooks/twilio")
async def handle_twilio_webhook(request: Request):
    """Handle inbound Twilio WhatsApp messages."""
    form_data = await request.form()
    
    from_number = form_data.get("From")  # whatsapp:+355...
    message_body = form_data.get("Body")
    message_sid = form_data.get("MessageSid")
    
    # Remove 'whatsapp:' prefix
    phone = from_number.replace("whatsapp:", "")
    
    # Process intent (STOP, PAUSE, etc.)
    await handle_user_intent(phone, message_body.upper())
    
    # Return empty 200 OK (Twilio doesn't care about response body)
    return Response(status_code=200)
```

## Transitioning to Meta Cloud API (Production)

When ready to migrate to Meta's direct API:

1. Implement a parallel `MetaWhatsAppProvider` with the same interface as `TwilioWhatsAppProvider`
2. Add a feature flag or env var to switch providers at startup
3. Update template format (Meta uses `{{variable_name}}` instead of `{{1}}`)
4. Redeploy with the new provider

The notification service's dispatch logic remains unchanged because both providers implement the same interface.

## Cost Comparison

| Provider | Per Message | Notes |
|----------|------------|-------|
| **Twilio** | $0.0075–$0.015 | Pay-as-you-go; reliable; testing sandbox free |
| **Meta Cloud API** | $0.002–$0.015 | Lower cost at scale; complex quality rating system |

At V1 scale (500 users, 1 digest/day), Twilio ≈ $2.50–$5/day. Meta would be cheaper once verified.

## References

- [Twilio WhatsApp API Docs](https://www.twilio.com/docs/whatsapp)
- [Twilio Message Templates](https://www.twilio.com/docs/whatsapp/messaging-templates)
- [Twilio Webhooks](https://www.twilio.com/docs/whatsapp/inbound-messages)
- See also: `../autoscout-backend/autoscout/notifications/` for implementation

## Support

For Twilio-specific issues, check the MCP context or refer to the Twilio dashboard logs under **Monitor > Logs > Conversations**.
