# 🚀 Chatello SaaS - Documentazione Completa Sistema

**Versione**: 2.0.0  
**Data**: 2025-08-05  
**Autore**: Team Chatello  
**Stato**: ✅ Production Ready (Manca solo integrazione pagamenti)

---

## 📋 Indice
1. [Architettura Sistema](#architettura-sistema)
2. [Componenti Implementati](#componenti-implementati)
3. [Componenti da Implementare](#componenti-da-implementare)
4. [Setup e Configurazione](#setup-e-configurazione)
5. [API Reference](#api-reference)
6. [Database Schema](#database-schema)
7. [Deployment e Manutenzione](#deployment-e-manutenzione)
8. [Troubleshooting](#troubleshooting)

---

## 🏗️ Architettura Sistema

### Overview
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   WordPress     │────▶│   SaaS API      │────▶│   AI Providers  │
│   Plugin v2.0   │     │ api.chatello.io │     │ OpenAI/Claude   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│  License Keys   │     │  Admin Dashboard │
│  Management     │     │  localhost:5012  │
└─────────────────┘     └─────────────────┘
```

### Stack Tecnologico
- **Backend API**: Flask + Gunicorn (Python 3.12)
- **Database**: MariaDB 11.4.5
- **Web Server**: Nginx con SSL Cloudflare
- **Caching**: Redis (per WordPress)
- **Monitoring**: Custom admin dashboard
- **Security**: Rate limiting, CORS, encryption

---

## ✅ Componenti Implementati

### 1. WordPress Plugin (v2.0)
**Directory**: `/var/www/wordpress/chatello.io/wp-content/plugins/AI-Assistenza-Prodotti-woocommerce-Plugin/`

**Funzionalità implementate**:
- ✅ Integrazione SaaS tramite `class-paa-saas.php`
- ✅ Validazione licenze online
- ✅ Switch automatico tra modalità Direct API e Proxy
- ✅ Pannello configurazione licenze in admin
- ✅ Logging debug per troubleshooting
- ✅ Supporto multi-provider (OpenAI, Anthropic, DeepSeek)
- ✅ Cache delle licenze per performance

**File chiave modificati**:
```php
// product-ai-assistant.php - Riga ~1590
if ($saas && $saas->is_ai_included()) {
    // Usa proxy SaaS per piani Pro/Agency
    $response = $saas->proxy_ai_request($api_provider, $messages, array(...));
} else {
    // Usa API dirette per piano Starter
    // Codice esistente...
}
```

### 2. SaaS API Backend
**URL**: `https://api.chatello.io`  
**Directory**: `/var/www/flask/chatello-saas/`  
**Port**: 5010 (interno, proxy via Nginx)

**Endpoints implementati**:
- ✅ `GET /` - Info API e endpoints disponibili
- ✅ `GET /api/health` - Health check
- ✅ `POST /api/validate` - Validazione licenze
- ✅ `POST /api/chat` - Proxy AI (richiede X-License-Key header)
- ✅ `GET /api/usage` - Statistiche utilizzo per licenza

**Features implementate**:
- ✅ Connection pooling MySQL
- ✅ Rate limiting (100 req/ora per licenza)
- ✅ CORS configurato per WordPress
- ✅ Logging completo in `/logs/api.log`
- ✅ Encryption API keys (AES-256-CBC)
- ✅ Environment variables in `.env`

**Configurazione Nginx**:
```nginx
# /etc/nginx/sites-available/api.chatello.io
server {
    listen 443 ssl;
    server_name api.chatello.io;
    
    location /api/ {
        proxy_pass http://127.0.0.1:5010;
        # Rate limiting e security headers configurati
    }
}
```

### 3. Admin Dashboard
**URL**: `http://localhost:5012` (solo via SSH tunnel)  
**Directory**: `/var/www/flask/chatello-saas/`  
**File**: `admin_dashboard.py`

**Pagine implementate**:
- ✅ Dashboard - Statistiche overview
- ✅ Customers - Gestione clienti
- ✅ Licenses - Gestione licenze
- ✅ Usage Analytics - Grafici utilizzo
- ✅ Create License - Form creazione licenze

**Features implementate**:
- ✅ Login con credenziali (admin/ChatelloAdmin2025!)
- ✅ Grafici con Chart.js
- ✅ Ricerca e filtri
- ✅ Export dati (UI pronta, logica TODO)
- ✅ Connection pool ottimizzato

### 4. Database Schema
**Database**: `chatello_saas`  
**User**: `chatello_saas` / `ChatelloSaaS2025!`

**Tabelle implementate**:
```sql
✅ plans           - Piani disponibili (starter, pro, agency)
✅ customers       - Informazioni clienti
✅ licenses        - Licenze con status e scadenza
✅ usage_logs      - Log utilizzo API con tokens
✅ payments        - Transazioni pagamenti (struttura pronta)
✅ api_keys        - Chiavi API criptate per Starter
✅ activity_logs   - Log attività sistema
```

**Dati iniziali inseriti**:
- 3 piani (Starter €2.99, Pro €7.99, Agency €19.99)
- 1 customer test
- 1 licenza test attiva

### 5. Sicurezza Implementata
- ✅ HTTPS con certificati Cloudflare
- ✅ Rate limiting per endpoint
- ✅ CORS headers configurati
- ✅ API key encryption in database
- ✅ SSH-only access per admin dashboard
- ✅ Session-based auth per admin
- ✅ Input validation e sanitization

---

## 🔧 Componenti da Implementare

### 1. Integrazione Paddle (PRIORITÀ ALTA)
**Obiettivo**: Gestione pagamenti ricorrenti e fatturazione automatica

**Todo list**:
```python
# Nuovo file: /var/www/flask/chatello-saas/paddle_integration.py
- [ ] Webhook handler per eventi Paddle
- [ ] Creazione automatica licenze dopo pagamento
- [ ] Gestione upgrade/downgrade piani
- [ ] Cancellazioni e rimborsi
- [ ] Sincronizzazione stato abbonamenti
```

**Endpoints da aggiungere**:
- `POST /api/paddle/webhook` - Riceve eventi da Paddle
- `POST /api/paddle/checkout` - Genera link checkout
- `GET /api/paddle/subscription/{id}` - Status abbonamento

**Database updates necessari**:
```sql
ALTER TABLE customers ADD paddle_user_id VARCHAR(100);
ALTER TABLE licenses ADD paddle_subscription_id VARCHAR(100);
ALTER TABLE payments ADD paddle_transaction_id VARCHAR(100);
```

### 2. Landing Page & Pricing (PRIORITÀ MEDIA)
**Obiettivo**: Pagina vendita con prezzi e checkout Paddle

**Todo list**:
- [ ] Design responsive landing page
- [ ] Integrazione Paddle.js per checkout
- [ ] Form raccolta email pre-launch
- [ ] Testimonials e use cases
- [ ] Documentazione pubblica

**Suggerimento struttura**:
```
https://chatello.io/
├── index.html         # Landing page
├── pricing.html       # Tabella prezzi
├── docs/             # Documentazione
└── checkout.html     # Paddle checkout
```

### 3. Email Automation (PRIORITÀ MEDIA)
**Obiettivo**: Comunicazioni automatiche con clienti

**Todo list**:
- [ ] Welcome email dopo registrazione
- [ ] Conferma attivazione licenza
- [ ] Avvisi scadenza (7 giorni prima)
- [ ] Receipt pagamenti
- [ ] Newsletter mensile utilizzo

**Integrazione suggerita**: SendGrid o AWS SES

### 4. API Pubblica (PRIORITÀ BASSA)
**Obiettivo**: Permettere integrazioni third-party

**Todo list**:
- [ ] API key management per developers
- [ ] Rate limiting per API keys
- [ ] Documentazione OpenAPI/Swagger
- [ ] SDK Python/PHP/Node.js
- [ ] Webhook per eventi licenze

### 5. Multi-tenancy (FUTURO)
**Obiettivo**: White label completo per Agency

**Todo list**:
- [ ] Custom domain per agency
- [ ] Branding personalizzabile
- [ ] Sub-accounts management
- [ ] Revenue sharing
- [ ] Report personalizzati

---

## 🚀 Setup e Configurazione

### Avvio Sistema Completo

```bash
# 1. Avvia API SaaS (già in esecuzione con gunicorn)
cd /var/www/flask/chatello-saas
source venv/bin/activate
# Già avviato automaticamente

# 2. Avvia Admin Dashboard
nohup python admin_dashboard.py > logs/admin.log 2>&1 &

# 3. Verifica servizi
curl https://api.chatello.io/api/health
```

### Accesso Admin Dashboard

```bash
# Da tuo computer locale
ssh -L 5012:localhost:5012 ubuntu@164.132.56.3

# Poi apri browser
http://localhost:5012
# Login: admin / ChatelloAdmin2025!
```

### Test Sistema Completo

```bash
# Test validazione licenza
curl -X POST https://api.chatello.io/api/validate \
  -H "Content-Type: application/json" \
  -H "X-License-Key: CHA-TEST-1234-5678-ABCD"

# Test proxy AI
curl -X POST https://api.chatello.io/api/chat \
  -H "Content-Type: application/json" \
  -H "X-License-Key: CHA-TEST-1234-5678-ABCD" \
  -d '{
    "messages": [{"role": "user", "content": "Test"}],
    "api_provider": "openai",
    "model": "gpt-3.5-turbo"
  }'
```

---

## 📚 API Reference

### Autenticazione
Tutte le richieste richiedono header `X-License-Key`:
```
X-License-Key: CHA-XXXX-XXXX-XXXX-XXXX
```

### Endpoints

#### POST /api/validate
Valida una licenza e ritorna informazioni.

**Request**:
```json
Headers: {
  "X-License-Key": "CHA-TEST-1234-5678-ABCD"
}
```

**Response**:
```json
{
  "valid": true,
  "plan": "pro",
  "expires_at": "2025-12-31",
  "features": {
    "ai_included": true,
    "sites_limit": 3
  },
  "usage": {
    "requests_used": 150,
    "requests_limit": 1000
  }
}
```

#### POST /api/chat
Proxy per richieste AI (solo Pro/Agency).

**Request**:
```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Hello"}
  ],
  "api_provider": "openai",
  "model": "gpt-3.5-turbo",
  "temperature": 0.7,
  "max_tokens": 500
}
```

**Response**:
```json
{
  "success": true,
  "provider": "openai",
  "response": {
    "choices": [{
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you?"
      }
    }]
  }
}
```

---

## 🗄️ Database Schema

### Tabella: licenses
```sql
CREATE TABLE licenses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    license_key VARCHAR(100) UNIQUE NOT NULL,
    customer_id INT NOT NULL,
    plan_id INT NOT NULL,
    status ENUM('active', 'suspended', 'expired', 'cancelled'),
    domain VARCHAR(255),
    expires_at DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (plan_id) REFERENCES plans(id)
);
```

### Tabella: usage_logs
```sql
CREATE TABLE usage_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    license_id INT NOT NULL,
    endpoint VARCHAR(100),
    tokens_used INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (license_id) REFERENCES licenses(id)
);
```

---

## 🔧 Deployment e Manutenzione

### Backup Database
```bash
# Backup manuale
mysqldump -u chatello_saas -p chatello_saas > backup_$(date +%Y%m%d).sql

# Restore
mysql -u chatello_saas -p chatello_saas < backup.sql
```

### Monitoraggio Logs
```bash
# API logs
tail -f /var/www/flask/chatello-saas/logs/api.log

# Admin logs
tail -f /var/www/flask/chatello-saas/logs/admin.log

# Nginx logs
tail -f /var/www/logs/nginx/api.chatello.io.access.log
```

### Update Codice
```bash
# Plugin WordPress
cd /var/www/wordpress/chatello.io/wp-content/plugins/AI-Assistenza-Prodotti-woocommerce-Plugin
git pull origin main

# Flask API
cd /var/www/flask/chatello-saas
git pull origin main  # (quando avrai un repo)
# Restart servizi
pkill -f "chatello-saas"
# Si riavvierà automaticamente
```

---

## 🐛 Troubleshooting

### Problema: "Pool exhausted" error
**Soluzione**: Aumenta pool_size in admin_dashboard.py (già fatto, ora è 10)

### Problema: "Mi dispiace, si è verificato un errore"
**Verifica**:
1. Check API key in .env è valida
2. Check licenza è attiva
3. Check logs per dettagli errore

### Problema: Dashboard non accessibile
**Verifica**:
1. SSH tunnel attivo
2. Admin dashboard in esecuzione
3. Porta 5012 non bloccata

### Problema: License validation fails
**Verifica**:
1. License key formato corretto
2. License non scaduta in DB
3. Customer esiste in DB

---

## 📞 Contatti e Supporto

**Development Team**:
- Plugin WordPress: `/AI-Assistenza-Prodotti-woocommerce-Plugin/`
- API Backend: `/var/www/flask/chatello-saas/`
- Database: MariaDB `chatello_saas`

**Server Access**:
- SSH: `ubuntu@164.132.56.3`
- Admin Dashboard: `http://localhost:5012` (via SSH tunnel)
- API: `https://api.chatello.io`

---

## 🎯 Next Sprint Priorities

1. **Integrazione Paddle** - Pagamenti automatici
2. **Landing Page** - Vendita self-service
3. **Email Automation** - Comunicazioni cliente
4. **Metriche avanzate** - Dashboard analytics
5. **Documentazione utente** - Guide e tutorial

---

**Ultimo aggiornamento**: 2025-08-05 06:35 UTC  
**Stato sistema**: ✅ Operativo al 100%  
**Prossimo sprint**: Integrazione Paddle + Landing Page