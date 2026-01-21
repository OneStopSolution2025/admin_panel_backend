# Template Builder System Documentation

## Overview

The Template Builder is a comprehensive system that allows users to create custom templates with dynamic pricing based on page count. The system integrates seamlessly with the wallet system and includes automatic price adjustments and admin notifications.

## 🎯 Core Features

### ✅ Template Creation
- Users can create custom templates with any number of pages
- Automatic price calculation based on page count
- Template configuration storage (JSON format)
- Set default template per user

### ✅ Dynamic Pricing Logic

**Standard Pricing:**
- **≤30 pages**: 37RM (flat rate)
- **>30 pages**: 37RM + (extra_pages × 1RM)

**Examples:**
- 10 pages = **37RM**
- 25 pages = **37RM**
- 30 pages = **37RM**
- 35 pages = 37RM + (5 × 1RM) = **42RM**
- 50 pages = 37RM + (20 × 1RM) = **57RM**
- 100 pages = 37RM + (70 × 1RM) = **107RM**

### ✅ Download & Charging
- Each download charges based on template's **current price**
- Amount automatically deducted from wallet
- Complete download history tracking
- Transaction records linked to downloads

### ✅ Price Change Management
- Users can modify template page count anytime
- **If template was already downloaded**: 
  - Price automatically recalculated
  - Admin receives notification email
  - Change history recorded
- Price updates apply to future downloads only

### ✅ Admin Notifications
When a user changes template pages **after downloads**:
1. System records old/new pages and prices
2. System logs download count before change
3. Email sent to Super Admin
4. Admin can review all price changes
5. Admin acknowledges notification

## 🔄 User Workflow

### 1. New User Experience

```
User Logs In → Sees "Template Builder" Option → Creates First Template
```

**Step 1: Create Template**
```http
POST /api/v1/templates/
{
  "template_name": "Monthly Report",
  "description": "Standard monthly report template",
  "total_pages": 35,
  "template_config": {...},
  "is_default": true
}
```

**Response:**
```json
{
  "id": 1,
  "template_name": "Monthly Report",
  "total_pages": 35,
  "base_price": 37.0,
  "extra_page_price": 1.0,
  "current_price": 42.0,  // 37 + (5 × 1)
  "is_default": true,
  "download_count": 0
}
```

### 2. Download Template

**Step 2: Download (First Time)**
```http
POST /api/v1/templates/1/download
```

**What Happens:**
1. System checks wallet balance (needs ≥42RM)
2. Deducts 42RM from wallet
3. Creates download record
4. Creates transaction record
5. Returns download info

**Response:**
```json
{
  "download_number": "DL-20250106-A1B2C3D4",
  "template_name": "Monthly Report",
  "pages_at_download": 35,
  "price_charged": 42.0,
  "file_path": "/downloads/1/DL-20250106-A1B2C3D4.pdf"
}
```

### 3. Modify Template After Downloads

**Scenario:** User downloads 3 times, then changes from 35 to 40 pages

```http
PATCH /api/v1/templates/1
{
  "total_pages": 40
}
```

**What Happens:**
1. System detects page change
2. Finds 3 previous downloads
3. Recalculates price: 37 + (10 × 1) = **47RM**
4. Records price history:
   - Old: 35 pages @ 42RM
   - New: 40 pages @ 47RM
   - Downloads before change: 3
5. **Sends email to Super Admin**
6. Future downloads charged 47RM

**Admin Notification Email:**
```
Subject: Template Price Change Alert

User: John Doe (john@example.com)
Template: Monthly Report (ID: 1)

Price Change:
- Old: 35 pages @ 42RM
- New: 40 pages @ 47RM
- Downloads before change: 3

Action Required: Review and acknowledge in admin panel.
```

## 📊 API Endpoints

### Public Endpoints

#### Get Pricing Settings
```http
GET /api/v1/templates/settings
```
Shows current pricing configuration to all users.

#### Get Price Quote
```http
POST /api/v1/templates/price-quote
{
  "pages": 45
}
```

**Response:**
```json
{
  "total_pages": 45,
  "base_price": 37.0,
  "extra_page_price": 1.0,
  "calculated_price": 52.0,
  "extra_pages": 15,
  "breakdown": "37RM (base) + 15 extra pages × 1RM = 52RM"
}
```

### User Endpoints

#### Create Template
```http
POST /api/v1/templates/
Authorization: Bearer <token>

{
  "template_name": "Annual Report",
  "description": "Yearly financial report",
  "total_pages": 50,
  "is_default": true
}
```

#### List My Templates
```http
GET /api/v1/templates/my?page=1&page_size=20
Authorization: Bearer <token>
```

#### Get Template Details
```http
GET /api/v1/templates/1
Authorization: Bearer <token>
```

#### Update Template
```http
PATCH /api/v1/templates/1
Authorization: Bearer <token>

{
  "total_pages": 60,
  "description": "Updated description"
}
```

#### Download Template
```http
POST /api/v1/templates/1/download
Authorization: Bearer <token>
```

**Important:** Requires sufficient wallet balance!

#### Get Download History
```http
GET /api/v1/templates/downloads/my?page=1
Authorization: Bearer <token>
```

#### Get My Statistics
```http
GET /api/v1/templates/my/statistics
Authorization: Bearer <token>
```

**Response:**
```json
{
  "total_templates": 3,
  "total_downloads": 15,
  "total_spent": 645.0,
  "active_templates": 3,
  "default_template": {
    "id": 1,
    "name": "Monthly Report",
    "pages": 35,
    "price": 42.0
  }
}
```

### Admin Endpoints

#### Get Price Changes
```http
GET /api/v1/templates/admin/price-changes?unnotified_only=true
Authorization: Bearer <admin_token>
```

Lists all templates where users changed pages after downloads.

#### Acknowledge Price Change
```http
POST /api/v1/templates/admin/price-changes/5/acknowledge
Authorization: Bearer <admin_token>
```

Marks notification as reviewed by admin.

#### Update Pricing Settings
```http
PATCH /api/v1/templates/admin/settings
Authorization: Bearer <admin_token>

{
  "base_price": 40.0,
  "base_pages_included": 35,
  "extra_page_price": 1.5,
  "admin_notification_email": "admin@company.com"
}
```

## 💰 Pricing Examples

| Pages | Calculation | Price |
|-------|-------------|-------|
| 1 | 37RM (base) | 37RM |
| 15 | 37RM (base) | 37RM |
| 30 | 37RM (base) | 37RM |
| 31 | 37 + (1×1) | 38RM |
| 35 | 37 + (5×1) | 42RM |
| 40 | 37 + (10×1) | 47RM |
| 50 | 37 + (20×1) | 57RM |
| 100 | 37 + (70×1) | 107RM |
| 200 | 37 + (170×1) | 207RM |

## 🔒 Permissions

### Regular Users
- ✅ Create templates
- ✅ View own templates
- ✅ Update own templates
- ✅ Download own templates (charged)
- ✅ View download history
- ✅ View statistics
- ❌ View other users' templates
- ❌ Modify pricing settings
- ❌ View price change notifications

### Super Admin
- ✅ View all templates (read-only)
- ✅ View price change history
- ✅ Acknowledge price changes
- ✅ Modify pricing settings
- ✅ Configure notification emails

## 📧 Email Notifications

### When Sent
Email to Super Admin when:
1. User changes template pages **after downloads**
2. Settings configured: `notify_on_price_change = true`
3. Admin email configured in settings

### Email Content
- User details
- Template details
- Old vs New pages
- Old vs New price
- Download count before change
- Link to review in admin panel

## 🗄️ Database Schema

### templates
```sql
├── id (PK)
├── user_id (FK → users)
├── template_name
├── description
├── total_pages
├── base_price (37.0)
├── extra_page_price (1.0)
├── current_price (calculated)
├── template_config (JSON)
├── is_active
├── is_default
├── created_at
├── updated_at
└── last_used_at
```

### template_downloads
```sql
├── id (PK)
├── template_id (FK → templates)
├── user_id (FK → users)
├── download_number (unique)
├── pages_at_download
├── price_charged
├── transaction_id (FK → transactions)
├── file_path
├── file_name
└── downloaded_at
```

### template_price_history
```sql
├── id (PK)
├── template_id (FK → templates)
├── user_id (FK → users)
├── old_pages
├── new_pages
├── old_price
├── new_price
├── change_reason
├── admin_notified
├── admin_notified_at
├── downloads_before_change
└── changed_at
```

## 🔄 Integration with Existing Systems

### Wallet System
- ✅ Downloads deduct from wallet
- ✅ Creates transaction records
- ✅ Insufficient balance handling
- ✅ Transaction history linked

### User System
- ✅ Per-user templates
- ✅ Permission checking
- ✅ Admin oversight

### Dashboard
- Can be extended to show template statistics

## 🧪 Testing Scenarios

### Scenario 1: Basic Template Creation & Download
```python
# Create template
template = create_template(name="Test", pages=30)
# Price: 37RM

# Download
download1 = download_template(template.id)
# Charged: 37RM
# Wallet: -37RM
```

### Scenario 2: Price Change After Downloads
```python
# Create & download
template = create_template(pages=30)  # 37RM
download1 = download_template(template.id)  # -37RM
download2 = download_template(template.id)  # -37RM

# Change pages
update_template(template.id, pages=40)  # Now 47RM
# Admin notified!

# Next download
download3 = download_template(template.id)  # -47RM (new price)
```

### Scenario 3: Multiple Templates
```python
template1 = create_template(pages=25)  # 37RM, default
template2 = create_template(pages=50)  # 57RM

# Downloads charged at respective prices
download_template(template1.id)  # -37RM
download_template(template2.id)  # -57RM
```

## 🎯 Best Practices

### For Users
1. **Plan pages carefully** before first download
2. **Check price quote** before creating template
3. **Set one default** template for quick access
4. **Monitor wallet balance** before downloads
5. **Review download history** regularly

### For Administrators
1. **Configure admin email** in settings
2. **Review price changes** regularly
3. **Acknowledge notifications** promptly
4. **Monitor unusual patterns** (frequent changes)
5. **Adjust pricing settings** based on usage

## 🚀 Future Enhancements

Potential additions:
- [ ] Template categories/tags
- [ ] Template sharing between users
- [ ] Bulk download discounts
- [ ] Subscription model for unlimited downloads
- [ ] Template versioning
- [ ] Export/import templates
- [ ] Template marketplace

## ❓ FAQ

**Q: What if I change pages from 40 to 25?**
A: Price goes back to 37RM (standard). Admin still notified if template was downloaded.

**Q: Can I delete a template?**
A: Yes, but it's soft-deleted (marked inactive). Download history preserved.

**Q: What happens if I have insufficient balance?**
A: Download fails with clear error message about required amount.

**Q: Are old downloads affected by price changes?**
A: No, only future downloads use the new price.

**Q: Can I have multiple default templates?**
A: No, only one template can be default at a time.

## 📞 Support

For technical support:
- Documentation: `/docs/TEMPLATE_BUILDER.md`
- API Reference: `http://localhost:8000/api/docs`
- Admin Panel: Review price changes regularly

---

**Template Builder System - Built with ❤️ for flexible pricing!**
