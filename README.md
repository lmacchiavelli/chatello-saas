# 🚀 Chatello SaaS - WordPress AI Plugin Backend

A complete SaaS backend for the Chatello WordPress AI plugin with MongoDB Atlas, featuring license management, AI proxy services, and a comprehensive admin dashboard with **Founders Deal** lifetime licensing.

## 📋 Features

### 🔑 License Management
- **Multiple Plans**: Starter (BYOK), Pro (AI Included), Agency (White Label)
- **🚀 Founders Deal**: Limited lifetime licenses (€29 one-time, 500 licenses max)
- **Automatic Validation**: Real-time license verification
- **Usage Tracking**: API calls, token consumption, rate limiting

### 🤖 AI Proxy Service
- **Multi-Provider Support**: OpenAI, Anthropic, DeepSeek
- **Centralized API Keys**: Pro/Agency users don't need their own keys
- **Rate Limiting**: Per-minute, per-hour, and monthly limits
- **Budget Management**: Token-based cost control

### 📊 Admin Dashboard
- **Real-Time Analytics**: MRR/ARR tracking, customer metrics
- **License Management**: Create, update, and monitor licenses
- **Founders Deal Tracking**: Progress visualization and revenue metrics
- **Financial Analytics**: Comprehensive SaaS business intelligence
- **API Key Management**: Centralized AI provider key configuration

## 🎯 Plans & Pricing

| Plan | Price | Features | API Keys | Sites | Requests |
|------|-------|----------|----------|-------|----------|
| **Starter** | €2.99/month | BYOK | User provides | 1 | Unlimited* |
| **Pro** | €7.99/month | AI Included | Shared | 3 | 1,000/month |
| **Agency** | €19.99/month | White Label + AI | Shared | Unlimited | 5,000/month |
| **🚀 Founders** | €29 **one-time** | **Lifetime License** | Shared | 5 | 2,000/month |

### 🔥 Founders Deal Special Features
- **Limited Offer**: Only 500 lifetime licenses available
- **One-Time Payment**: €29 instead of €7.99/month
- **Special Badge**: "Founders Member" status
- **Early Access**: New features before regular customers
- **Priority Support**: Enhanced customer service

## 📦 Installation

```bash
# Clone repository
git clone https://github.com/yourusername/chatello-saas.git
cd chatello-saas

# Setup environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your credentials

# Initialize database
python setup_mongodb.py

# Start services
gunicorn --config gunicorn.conf.py app:app
```

## 🔌 API Usage

### License Validation
```bash
curl -X POST https://api.chatello.io/api/validate \
  -H "X-License-Key: CHA-XXXX-XXXX-XXXX-XXXX"
```

### Response for Founders Deal
```json
{
  "valid": true,
  "license": {
    "is_lifetime": true,
    "is_founders_deal": true
  },
  "plan": {
    "name": "founders",
    "price": 29.0
  },
  "founders_deal": {
    "badge": "founders_member",
    "total_sold": 1,
    "remaining_licenses": 499,
    "thank_you_message": "🚀 Thank you for being a Founder!"
  }
}
```

## 📊 Admin Dashboard Access

```bash
# SSH tunnel (production)
ssh -L 5011:localhost:5011 ubuntu@your-server

# Browser
http://localhost:5011
# Login: admin / ChatelloAdmin2025!
```

## 📈 Business Model

- **MRR Target**: €5,000/month recurring revenue
- **Founders Bootstrap**: €14,500 immediate cash flow (500 × €29)
- **Hybrid Model**: Recurring subscriptions + one-time lifetime deals
- **FOMO Strategy**: Limited 500 licenses create urgency

## 🔒 Security Features

- SSH tunnel only admin access
- API rate limiting and validation
- MongoDB Atlas replica sets
- Environment variable configuration
- HTTPS-only communications

## 🚀 Production Ready

This codebase includes:
- ✅ Real-time MongoDB analytics
- ✅ Founders Deal implementation
- ✅ Production-grade error handling
- ✅ Comprehensive logging
- ✅ Security best practices
- ✅ Scalable architecture

---

**Built for SaaS success with immediate revenue generation through the innovative Founders Deal model!**