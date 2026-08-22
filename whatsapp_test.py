from twilio.rest import Client
from whatsapp_config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM, MY_WHATSAPP_NUMBER

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

message = client.messages.create(
    from_=TWILIO_WHATSAPP_FROM,
    body="Test message from MODI1 🚀",
    to=MY_WHATSAPP_NUMBER
)

print("Message sent! SID:", message.sid)