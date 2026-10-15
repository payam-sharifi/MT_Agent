---
name: support-chat
description: When the customer wants a human (پشتیبانی، Support-Team, talk to a person), record their message with record_support_message so it appears in the admin inbox. Also use it when they answer a message from the support team.
---

# Human support chat

Customers can talk to the human support team from Telegram or WhatsApp. Those messages show in the admin inbox. Admin replies arrive in the same chat with the label "پیام از تیم پشتیبانی".

Tools: `record_support_message`, `list_support_thread`.

## Tell them they can

When you introduce the site or they seem stuck, mention once that they can write to the support team any time. Do not push it every turn.

## When they ask for support

Phrases like:

- "میخوام با پشتیبانی صحبت کنم" / "تیم پشتیبانی" / "آدم واقعی"
- "I want to talk to support" / "human please"
- "Support-Team" / "einen Menschen"

Do this:

1. Take `identifier` and `platform` from the lookup line.
2. Call `record_support_message(identifier, platform, message)` with their words.
3. Tell them the support team received it and will reply in this same chat. If `list_support_thread` shows a waiting admin reply, read it to them — do not invent a reply.
4. Do **not** treat it as a website edit. Do not call `update_website_content` for this.

If they only said they want support and gave no details, still record that, then ask what they need so the next message can be recorded too.

## When they answer the support team

If they mention a message from support, or they are clearly answering a human (not asking you to change the site):

1. Optionally call `list_support_thread` to see the last messages.
2. Call `record_support_message` with their reply.
3. Confirm it was sent to the support team.

If the same message also asks for a site change, do the site change as usual **and** record the support part only if they asked for a human.

## Do not

- Do not invent a support reply. You are not the support team.
- Do not send the visitor contact-form leads here (`list_website_leads` is a different thing).
- Do not refuse with the generic out-of-scope line when they ask for support. This is in scope.
