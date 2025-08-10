# 🧪 Chatello SaaS API - Endpoint Testing Guide

## 📋 New API Endpoints Implemented (2025-08-09)

**Version**: 2.1.0  
**Features**: Multi-level rate limiting, token tracking, budget management, real-time analytics

---

## 🔑 Authentication

All authenticated endpoints require the `X-License-Key` header:

```bash
-H "X-License-Key: CHA-B21AF1CF-BD99A579-01F8A4C0-ECFA58EB"
```

**Available Test License Keys:**
- **Pro Plan**: `CHA-B21AF1CF-BD99A579-01F8A4C0-ECFA58EB` (AI Included)
- **Starter Plan**: `CHA-F0E17C9E-4A7164DE-29427E34-AB0EA5EC` (BYOK)

---

## 📊 Usage Analytics Endpoints

### 1. **GET /api/usage/current** - Current Usage Dashboard
**Purpose**: Get real-time usage statistics with 80% warnings  
**Authentication**: Required  
**Rate Limit**: 10/minute  

```bash
curl -s https://api.chatello.io/api/usage/current \
  -H "X-License-Key: CHA-B21AF1CF-BD99A579-01F8A4C0-ECFA58EB"
```

**Response Structure:**
```json
{
  "status": "success",
  "license_key": "CHA-...",
  "plan": {
    "name": "pro",
    "display_name": "Pro - AI Inclusa",
    "price": 7.99
  },
  "current_usage": {
    "current_month": {
      "requests": 0,
      "tokens": 0,
      "cost_eur": 0.0,
      "avg_response_time_ms": 0
    },
    "current_hour": {"requests": 0},
    "current_minute": {"requests": 0},
    "limits": {
      "monthly_requests": 1000,
      "requests_per_minute": 10,
      "requests_per_hour": 200,
      "monthly_budget_eur": 4.0
    },
    "usage_percentages": {
      "requests": 0.0,
      "budget": 0
    }
  },
  "warnings": [],
  "timestamp": "2025-08-09T07:39:28.859012"
}
```

### 2. **GET /api/usage/history** - Historical Analytics
**Purpose**: Detailed usage history with daily breakdown  
**Authentication**: Required  
**Rate Limit**: 5/minute  
**Parameters**: `days` (1-90), `provider` (openai/anthropic/deepseek)  

```bash
# Last 30 days
curl -s "https://api.chatello.io/api/usage/history?days=30" \
  -H "X-License-Key: CHA-B21AF1CF-BD99A579-01F8A4C0-ECFA58EB"

# Last 7 days, OpenAI only  
curl -s "https://api.chatello.io/api/usage/history?days=7&provider=openai" \
  -H "X-License-Key: CHA-B21AF1CF-BD99A579-01F8A4C0-ECFA58EB"
```

**Response Structure:**
```json
{
  "status": "success",
  "license_key": "CHA-...",
  "period": {
    "start": "2025-08-02T07:39:32.860513",
    "end": "2025-08-09T07:39:32.860513",
    "days": 7
  },
  "daily_usage": {
    "2025-08-08": {
      "total_requests": 25,
      "total_tokens": 1500,
      "avg_response_time": 245,
      "by_provider": {
        "openai": {"requests": 15, "tokens": 900, "avg_response_time": 230},
        "anthropic": {"requests": 10, "tokens": 600, "avg_response_time": 267}
      }
    }
  },
  "recent_requests": [
    {
      "endpoint": "/api/chat/openai",
      "provider": "openai",
      "model": "gpt-4o-mini",
      "tokens_used": 150,
      "response_time_ms": 245,
      "created_at": "2025-08-09T07:30:15",
      "ip_address": "192.168.1.100"
    }
  ],
  "summary": {
    "total_requests": 25,
    "total_tokens": 1500,
    "days_with_usage": 1,
    "avg_requests_per_day": 25.0
  }
}
```

---

## ⚡ Limits Validation Endpoint

### 3. **GET /api/limits/check** - Pre-Request Validation
**Purpose**: Check all limits before making API requests  
**Authentication**: Required  
**Rate Limit**: 20/minute  
**HTTP Codes**: 200 (OK), 429 (Rate Limited), 402 (Budget Exceeded)  

```bash
curl -s https://api.chatello.io/api/limits/check \
  -H "X-License-Key: CHA-B21AF1CF-BD99A579-01F8A4C0-ECFA58EB"
```

**Response Structure:**
```json
{
  "status": "success",
  "license_key": "CHA-...",
  "can_make_request": true,
  "limits_status": {
    "monthly_requests": {
      "passed": true,
      "current": 0,
      "limit": 1000,
      "percentage": 0.0
    },
    "requests_per_minute": {
      "passed": true,
      "current": 0,
      "limit": 10
    },
    "requests_per_hour": {
      "passed": true,
      "current": 0,
      "limit": 200
    },
    "monthly_budget": {
      "passed": true,
      "current_cost_eur": 0.0,
      "limit_eur": 4.0,
      "percentage": 0
    }
  },
  "blocking_factors": [],
  "reset_times": {
    "next_minute": "2025-08-09T08:00:00",
    "next_hour": "2025-08-09T09:00:00",
    "next_month": "2025-09-01T00:00:00"
  }
}
```

---

## 🔄 Legacy & Public Endpoints

### 4. **GET /api/usage/{license_key}** - Legacy Endpoint
**Purpose**: Backward compatibility for existing integrations  
**Authentication**: License key in URL  
**Rate Limit**: 10/minute  

```bash
curl -s https://api.chatello.io/api/usage/CHA-B21AF1CF-BD99A579-01F8A4C0-ECFA58EB
```

### 5. **POST /api/validate** - License Validation
**Purpose**: Validate license and get plan info  
**Authentication**: X-License-Key header  

```bash
curl -s -X POST https://api.chatello.io/api/validate \
  -H "X-License-Key: CHA-B21AF1CF-BD99A579-01F8A4C0-ECFA58EB"
```

### 6. **GET /api/health** - Health Check
**Purpose**: Public health check endpoint  
**Authentication**: None  

```bash
curl -s https://api.chatello.io/api/health
```

---

## 🤖 AI Proxy Endpoint

### 7. **POST /api/chat** - AI Proxy Service
**Purpose**: Proxy AI requests for Pro/Agency users  
**Authentication**: Required  
**Rate Limit**: 100/hour + plan limits  

```bash
curl -s -X POST https://api.chatello.io/api/chat \
  -H "X-License-Key: CHA-B21AF1CF-BD99A579-01F8A4C0-ECFA58EB" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, test message"}
    ],
    "api_provider": "openai",
    "model": "gpt-4o-mini",
    "max_tokens": 100
  }'
```

---

## 📈 Testing Scenarios

### **Scenario 1: Rate Limit Testing**
```bash
# Test per-minute limit (10 requests for Pro)
for i in {1..15}; do
  echo "Request $i:"
  curl -s https://api.chatello.io/api/limits/check \
    -H "X-License-Key: CHA-B21AF1CF-BD99A579-01F8A4C0-ECFA58EB" \
    | grep -E "(can_make_request|blocking_factors)"
done
```

### **Scenario 2: Budget Validation**
```bash
# Check budget status
curl -s https://api.chatello.io/api/usage/current \
  -H "X-License-Key: CHA-B21AF1CF-BD99A579-01F8A4C0-ECFA58EB" \
  | grep -A 5 "monthly_budget"
```

### **Scenario 3: Error Handling**
```bash
# Invalid license key
curl -s https://api.chatello.io/api/usage/current \
  -H "X-License-Key: INVALID-KEY-TEST" \
  | grep error

# Missing license key
curl -s https://api.chatello.io/api/usage/current
```

---

## ⚠️ Alert System (80% Threshold)

The API automatically includes warnings when usage approaches limits:

- **Monthly requests ≥ 80%**: "Monthly request limit approaching (>80%)"
- **Monthly budget ≥ 80%**: "Monthly budget limit approaching (>80%)"

Example response with warnings:
```json
{
  "warnings": [
    "Monthly request limit approaching (>80%)",
    "Monthly budget limit approaching (>80%)"
  ]
}
```

---

## 🔧 Integration Examples

### **WordPress Plugin Integration**
```php
// Check limits before making request
$limits_check = wp_remote_get('https://api.chatello.io/api/limits/check', [
    'headers' => ['X-License-Key' => $license_key]
]);

if (wp_remote_retrieve_response_code($limits_check) === 200) {
    $limits_data = json_decode(wp_remote_retrieve_body($limits_check), true);
    if ($limits_data['can_make_request']) {
        // Proceed with API request
        make_ai_request();
    } else {
        // Handle rate limit or budget exceeded
        handle_limits_exceeded($limits_data['blocking_factors']);
    }
}
```

### **JavaScript Dashboard**
```javascript
// Get current usage for dashboard
async function getCurrentUsage(licenseKey) {
    const response = await fetch('https://api.chatello.io/api/usage/current', {
        headers: { 'X-License-Key': licenseKey }
    });
    
    if (response.ok) {
        const data = await response.json();
        updateUsageDashboard(data.current_usage);
        
        // Show warnings if any
        if (data.warnings.length > 0) {
            showWarnings(data.warnings);
        }
    }
}
```

---

## 📊 Response Codes Summary

| Code | Meaning | Scenario |
|------|---------|----------|
| **200** | Success | Request completed successfully |
| **401** | Unauthorized | Invalid or missing license key |
| **402** | Payment Required | Monthly budget exceeded |  
| **404** | Not Found | License not found |
| **429** | Too Many Requests | Rate limit exceeded |
| **500** | Server Error | Internal server error |

---

## 🎯 Testing Checklist

- [✅] **GET /api/usage/current** - Real-time usage with warnings
- [✅] **GET /api/usage/history** - Historical data with filters  
- [✅] **GET /api/limits/check** - Pre-request validation
- [✅] **Rate limiting** - Per minute/hour/month limits
- [✅] **Budget tracking** - Token cost calculation
- [✅] **Error handling** - Proper HTTP codes
- [✅] **Authentication** - License key validation
- [✅] **Legacy compatibility** - /api/usage/{key} endpoint

**Status**: ✅ **All endpoints implemented and tested successfully**

---

*Last Updated: 2025-08-09 - API Version 2.1.0*