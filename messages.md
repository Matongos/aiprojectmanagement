# Odoo Messaging System Technical Guide

## Overview
Odoo's messaging system is a comprehensive framework that handles internal communication, email notifications, and document following. It's built on top of several core models that work together to provide a flexible and powerful messaging infrastructure.

## Core Models

### 1. mail.message
The central model for storing all messages in the system.

```python
class Message(models.Model):
    _name = 'mail.message'
    
    # Message Content
    subject = fields.Char('Subject')
    body = fields.Html('Contents')
    message_type = fields.Selection([
        ('email', 'Incoming Email'),
        ('comment', 'Comment'),
        ('email_outgoing', 'Outgoing Email'),
        ('notification', 'System notification'),
        ('auto_comment', 'Automated Targeted Notification'),
        ('user_notification', 'User Specific Notification')
    ])
    
    # Document Reference
    model = fields.Char('Related Document Model')
    res_id = fields.Many2oneReference('Related Document ID')
    record_name = fields.Char('Message Record Name')
    
    # Author Information
    author_id = fields.Many2one('res.partner', 'Author')
    email_from = fields.Char('From')
    
    # Message Metadata
    date = fields.Datetime('Date')
    message_id = fields.Char('Message-Id')
    subtype_id = fields.Many2one('mail.message.subtype', 'Subtype')
```

### 2. mail.followers
Manages document following and notification preferences.

```python
class Followers(models.Model):
    _name = 'mail.followers'
    
    res_model = fields.Char('Related Document Model')
    res_id = fields.Many2oneReference('Related Document ID')
    partner_id = fields.Many2one('res.partner', 'Related Partner')
    subtype_ids = fields.Many2many('mail.message.subtype', 'Subtype')
```

### 3. mail.notification
Handles message delivery status and recipient information.

```python
class MailNotification(models.Model):
    _name = 'mail.notification'
    
    mail_message_id = fields.Many2one('mail.message', 'Message')
    res_partner_id = fields.Many2one('res.partner', 'Recipient')
    notification_type = fields.Selection([
        ('inbox', 'Inbox'),
        ('email', 'Email')
    ])
    notification_status = fields.Selection([
        ('ready', 'Ready to Send'),
        ('sent', 'Delivered'),
        ('bounce', 'Bounced'),
        ('exception', 'Exception')
    ])
    is_read = fields.Boolean('Is Read')
```

## Message Flow

1. **Message Creation**
   - Messages can be created through various channels:
     - User comments in the chatter
     - Email incoming through the mail gateway
     - System notifications
     - Automated messages

2. **Recipient Determination**
   - Recipients are determined through:
     - Document followers (mail.followers)
     - Explicit mentions (@user)
     - System rules (e.g., task assignees)

3. **Notification Processing**
   - Each recipient gets a notification record
   - Notifications are processed based on user preferences:
     - Inbox notifications for internal users
     - Email notifications for external users

## Following System

1. **Document Following**
   - Users can follow documents through:
     - Manual subscription
     - Automatic following (e.g., when assigned)
     - Project-level following

2. **Notification Preferences**
   - Users can set their notification preferences:
     - Handle by Emails
     - Handle in Odoo Inbox
   - Subtype-based filtering:
     - Users can choose which types of messages to receive
     - Different subtypes for different document types

## Message Types

1. **Comment**
   - Regular user messages
   - Visible in the chatter
   - Can be internal or external

2. **Email**
   - Incoming and outgoing emails
   - Can be converted to internal notes
   - Supports email threading

3. **Notification**
   - System-generated messages
   - Document state changes
   - Automated updates

## Implementation Example

```python
# Adding a follower to a document
def message_subscribe(self, partner_ids=None, subtype_ids=None):
    """Subscribe partners to the document."""
    if not subtype_ids:
        project_followers = self.project_id.message_follower_ids.filtered(
            lambda f: f.partner_id.id in partner_ids
        )
        for project_follower in project_followers:
            project_subtypes = project_follower.subtype_ids
            task_subtypes = (
                project_subtypes.mapped('parent_id') | 
                project_subtypes.filtered(lambda sub: sub.internal or sub.default)
            ).ids
            partner_ids.remove(project_follower.partner_id.id)
            super().message_subscribe(
                project_follower.partner_id.ids, 
                task_subtypes
            )
    return super().message_subscribe(partner_ids, subtype_ids)

# Sending a notification
def _notify_thread_by_email(self, message, recipients_data, **kwargs):
    """Send email notifications to recipients."""
    for recipient in recipients_data:
        mail_values = self._notify_by_email_get_final_mail_values(
            recipient,
            base_mail_values,
            additional_values={'body_html': mail_body}
        )
        new_email = self.env['mail.mail'].create(mail_values)
        
        # Create notification records
        self.env['mail.notification'].create({
            'author_id': message.author_id.id,
            'mail_mail_id': new_email.id,
            'mail_message_id': message.id,
            'notification_status': 'ready',
            'notification_type': 'email',
            'res_partner_id': recipient['id'],
        })
```

## Best Practices

1. **Message Creation**
   - Always specify the correct message_type
   - Include proper document references
   - Set appropriate subtypes

2. **Follower Management**
   - Use message_subscribe for adding followers
   - Consider notification preferences
   - Handle subtype inheritance

3. **Notification Handling**
   - Process notifications asynchronously
   - Handle delivery failures gracefully
   - Maintain notification history

4. **Security**
   - Check access rights before sending messages
   - Validate email addresses
   - Handle sensitive information appropriately

## Database Schema

### mail_message
- id: Primary key
- message_type: Type of message
- model: Related document model
- res_id: Related document ID
- body: Message content
- author_id: Message author
- email_from: Sender email
- date: Message date
- message_id: Unique message identifier

### mail_followers
- id: Primary key
- res_model: Document model
- res_id: Document ID
- partner_id: Follower partner
- subtype_ids: Notification subtypes

### mail_notification
- id: Primary key
- mail_message_id: Related message
- res_partner_id: Recipient
- notification_type: Type of notification
- notification_status: Delivery status
- is_read: Read status 