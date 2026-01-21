# Ticket System Documentation

## Overview

The ticket system is a comprehensive support ticket management solution integrated into the Admin Panel Backend. It provides full ticketing capabilities for customer support, bug reporting, and general inquiries.

## Features

### ✅ Core Ticket Management
- Create, read, update tickets
- Automatic ticket number generation (TKT-YYYYMMDD-XXXX)
- Multiple status tracking
- Priority levels
- Category classification
- Tag support

### ✅ Communication
- Add comments/replies to tickets
- Internal notes (staff only)
- Resolution marking
- Comment history tracking

### ✅ Assignment & Workflow
- Assign tickets to support staff
- Auto-status transitions
- Status change history
- Activity audit trail

### ✅ SLA Management
- Configurable SLA by priority
- First response time tracking
- Resolution time tracking
- Business hours support

### ✅ Analytics & Reporting
- Ticket statistics by status, priority, category
- Average response times
- Average resolution times
- SLA compliance tracking

## Ticket Properties

### Ticket Statuses
- **OPEN**: Newly created, awaiting response
- **IN_PROGRESS**: Being worked on
- **WAITING_ON_CUSTOMER**: Awaiting customer response
- **RESOLVED**: Issue resolved, awaiting closure
- **CLOSED**: Ticket fully closed
- **REOPENED**: Previously closed, reopened by user

### Priority Levels
- **URGENT**: Critical issues, 15 min first response
- **HIGH**: High importance, 1 hour first response
- **MEDIUM**: Standard priority, 4 hours first response
- **LOW**: Low priority, 8 hours first response

### Categories
- **TECHNICAL_SUPPORT**: Technical issues
- **BILLING**: Payment and billing inquiries
- **ACCOUNT**: Account-related questions
- **FEATURE_REQUEST**: New feature suggestions
- **BUG_REPORT**: Bug reports
- **GENERAL_INQUIRY**: General questions
- **OTHER**: Other topics

## API Endpoints

### Create Ticket
```http
POST /api/v1/tickets/
Authorization: Bearer <token>
Content-Type: application/json

{
  "subject": "Unable to generate report",
  "description": "When I click generate report, I get an error...",
  "priority": "high",
  "category": "technical_support",
  "tags": "report,error"
}
```

**Response:**
```json
{
  "id": 123,
  "ticket_number": "TKT-20250106-0001",
  "user_id": 1,
  "subject": "Unable to generate report",
  "description": "When I click generate report...",
  "status": "open",
  "priority": "high",
  "category": "technical_support",
  "created_at": "2025-01-06T10:00:00Z"
}
```

### List My Tickets
```http
GET /api/v1/tickets/my?page=1&page_size=20&status=open
Authorization: Bearer <token>
```

### Get Ticket Details
```http
GET /api/v1/tickets/123
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": 123,
  "ticket_number": "TKT-20250106-0001",
  "subject": "Unable to generate report",
  "description": "When I click generate report...",
  "status": "open",
  "priority": "high",
  "category": "technical_support",
  "creator_name": "John Doe",
  "creator_email": "john@example.com",
  "assigned_to_name": "Support Agent",
  "assigned_to_email": "support@company.com",
  "comments_count": 3,
  "attachments_count": 1,
  "created_at": "2025-01-06T10:00:00Z",
  "first_response_at": "2025-01-06T10:30:00Z"
}
```

### Add Comment
```http
POST /api/v1/tickets/123/comments
Authorization: Bearer <token>
Content-Type: application/json

{
  "comment": "I've tried clearing my cache but the issue persists",
  "is_internal": false
}
```

### Assign Ticket (Admin Only)
```http
POST /api/v1/tickets/123/assign
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "assigned_to_id": 5,
  "note": "Assigning to Sarah from tech support"
}
```

### Change Status
```http
POST /api/v1/tickets/123/status
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "resolved",
  "note": "Issue has been fixed in the latest release",
  "is_resolution": true
}
```

### Get Ticket Statistics (Admin Only)
```http
GET /api/v1/tickets/statistics/overview?start_date=2025-01-01
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "total_tickets": 150,
  "open_tickets": 25,
  "in_progress_tickets": 40,
  "resolved_tickets": 70,
  "closed_tickets": 15,
  "tickets_by_priority": {
    "urgent": 10,
    "high": 30,
    "medium": 80,
    "low": 30
  },
  "tickets_by_category": {
    "technical_support": 60,
    "billing": 30,
    "account": 20,
    "bug_report": 25,
    "feature_request": 10,
    "general_inquiry": 5
  },
  "average_resolution_time": 18.5,
  "average_first_response_time": 2.3
}
```

## Permissions

### Users (Individual/Enterprise/Sub-user)
- ✅ Create tickets
- ✅ View their own tickets
- ✅ Comment on their own tickets
- ✅ Reopen their closed tickets
- ❌ View other users' tickets
- ❌ Assign tickets
- ❌ Add internal notes
- ❌ View statistics

### Super Admin
- ✅ View all tickets
- ✅ Assign tickets to staff
- ✅ Change any ticket status
- ✅ Add internal notes
- ✅ View ticket statistics
- ✅ Bulk operations
- ✅ Configure SLA settings

## Workflow Examples

### Standard Support Flow

1. **User creates ticket** → Status: OPEN
2. **Admin assigns to support staff** → Status: IN_PROGRESS
3. **Staff adds response** → First response time recorded
4. **User replies** → Ticket remains IN_PROGRESS
5. **Staff resolves issue** → Status: RESOLVED (resolution time recorded)
6. **User confirms** or **Auto-close after 48h** → Status: CLOSED

### User Reopening Flow

1. **Ticket is CLOSED**
2. **User adds new comment** → Status: REOPENED
3. **Staff reviews** → Status: IN_PROGRESS
4. **Issue addressed** → Status: RESOLVED
5. **Confirmed** → Status: CLOSED

## SLA Configuration

Default SLA times (can be configured per priority):

| Priority | First Response | Resolution Time |
|----------|---------------|-----------------|
| Urgent   | 15 minutes    | 4 hours         |
| High     | 1 hour        | 8 hours         |
| Medium   | 4 hours       | 24 hours        |
| Low      | 8 hours       | 48 hours        |

### Configuring SLA

```http
POST /api/v1/tickets/sla/config
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "priority": "urgent",
  "first_response_time": 10,
  "resolution_time": 120,
  "applies_business_hours_only": true
}
```

## Database Schema

### Tickets Table
```sql
tickets
├── id (PK)
├── ticket_number (unique)
├── user_id (FK → users)
├── assigned_to_id (FK → users)
├── subject
├── description
├── status
├── priority
├── category
├── first_response_at
├── resolved_at
├── closed_at
├── tags
├── is_internal
├── created_at
└── updated_at
```

### Ticket Comments Table
```sql
ticket_comments
├── id (PK)
├── ticket_id (FK → tickets)
├── user_id (FK → users)
├── comment
├── is_internal
├── is_resolution
├── created_at
└── updated_at
```

### Ticket Status History Table
```sql
ticket_status_history
├── id (PK)
├── ticket_id (FK → tickets)
├── changed_by_id (FK → users)
├── from_status
├── to_status
├── from_priority
├── to_priority
├── from_assigned_to_id
├── to_assigned_to_id
├── change_note
└── changed_at
```

## Integration with Existing System

The ticket system is **fully integrated** with the existing backend:

### User System Integration
- Uses existing user authentication
- Respects existing role-based permissions
- Super Admin has full ticket access
- Regular users see only their tickets

### Dashboard Integration
- Ticket counts added to Super Admin dashboard
- Open vs resolved ticket metrics
- Integrated with existing analytics

### No Impact on Existing Features
- ✅ Wallet system unchanged
- ✅ Activity tracking unchanged
- ✅ User management unchanged
- ✅ All existing APIs work as before

## Usage Examples

### For End Users

```python
# Create a support ticket
import requests

token = "your_access_token"
headers = {"Authorization": f"Bearer {token}"}

ticket_data = {
    "subject": "Cannot access my wallet",
    "description": "I'm getting a 'wallet not found' error",
    "priority": "high",
    "category": "technical_support"
}

response = requests.post(
    "http://api.example.com/api/v1/tickets/",
    json=ticket_data,
    headers=headers
)

ticket = response.json()
print(f"Ticket created: {ticket['ticket_number']}")

# Add a comment
comment_data = {
    "comment": "I tried logging out and back in, but the issue persists"
}

requests.post(
    f"http://api.example.com/api/v1/tickets/{ticket['id']}/comments",
    json=comment_data,
    headers=headers
)
```

### For Administrators

```python
# Get all open tickets
response = requests.get(
    "http://api.example.com/api/v1/tickets/?status=open",
    headers={"Authorization": f"Bearer {admin_token}"}
)

open_tickets = response.json()

# Assign ticket to support staff
for ticket in open_tickets:
    if ticket['priority'] == 'urgent':
        requests.post(
            f"http://api.example.com/api/v1/tickets/{ticket['id']}/assign",
            json={"assigned_to_id": support_staff_id},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

# Get statistics
stats_response = requests.get(
    "http://api.example.com/api/v1/tickets/statistics/overview",
    headers={"Authorization": f"Bearer {admin_token}"}
)

stats = stats_response.json()
print(f"Average resolution time: {stats['average_resolution_time']} hours")
```

## Best Practices

### For Users
1. **Be specific** in ticket subject lines
2. **Provide details** in the description
3. **Use appropriate priority** levels
4. **Choose correct category** for faster routing
5. **Respond promptly** when staff requests information

### For Support Staff
1. **Acknowledge tickets quickly** (first response SLA)
2. **Keep customers updated** on progress
3. **Use internal notes** for team communication
4. **Mark resolution comments** clearly
5. **Update status** as work progresses

### For Administrators
1. **Monitor SLA compliance** regularly
2. **Balance ticket load** across staff
3. **Review statistics** to identify trends
4. **Update SLA configs** based on team capacity
5. **Use tags** for categorization and reporting

## Future Enhancements

Planned features (not yet implemented):
- [ ] Email notifications for ticket updates
- [ ] File attachments support
- [ ] Ticket templates
- [ ] Auto-assignment rules
- [ ] Custom fields
- [ ] Ticket merging
- [ ] Customer satisfaction surveys
- [ ] Integration with external ticketing systems

## Troubleshooting

### Common Issues

**Q: Users can't see assigned tickets**
A: Ensure the assignment API includes proper notifications

**Q: SLA times not calculating correctly**
A: Check business hours configuration in SLA settings

**Q: Internal notes visible to users**
A: Verify `is_internal` flag is set to `true`

**Q: Ticket number duplicates**
A: This shouldn't happen with the current implementation; check database constraints

## Support

For technical support on the ticket system:
- Documentation: `/docs/TICKET_SYSTEM.md`
- API Reference: `http://localhost:8000/api/docs`
- GitHub Issues: For bug reports and feature requests
