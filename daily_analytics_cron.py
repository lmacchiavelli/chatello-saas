#!/usr/bin/env python3
"""
Daily Analytics Cron Job for Chatello SaaS
Automatically runs every day to collect analytics data and events
"""

import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mongodb_schema import (
    save_daily_analytics_with_events,
    check_and_create_milestones,
    create_business_event
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/www/flask/chatello-saas/logs/daily_cron.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb+srv://lmacchiavelli:BINI9RIhBOvjy3eu@chatello.38m5lpq.mongodb.net/?retryWrites=true&w=majority&appName=chatello')
DATABASE_NAME = os.environ.get('MONGODB_DATABASE', 'chatello_saas')

def analyze_growth_trends(db):
    """
    Analyze growth trends and create relevant business events
    """
    try:
        # Get data from last 7 days for trend analysis
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        # Get historical analytics data
        recent_analytics = list(db.historical_analytics.find({
            'period_type': 'daily',
            'date': {'$gte': seven_days_ago}
        }).sort('date', 1))
        
        if len(recent_analytics) < 2:
            logger.info("Not enough historical data for trend analysis")
            return
        
        # Compare latest vs 7 days ago
        latest = recent_analytics[-1]
        oldest = recent_analytics[0]
        
        # Calculate growth metrics
        customer_growth = latest['total_customers'] - oldest['total_customers']
        paying_growth = latest['paying_customers'] - oldest['paying_customers']
        mrr_growth = latest['mrr'] - oldest['mrr']
        
        # Create events based on significant changes
        if customer_growth >= 5:  # 5+ new customers in 7 days
            create_business_event(
                db,
                'milestone_reached',
                f"🚀 Crescita accelerata: +{customer_growth} nuovi clienti in 7 giorni!",
                metadata={'growth_period': '7_days', 'customer_growth': customer_growth}
            )
        
        if paying_growth >= 3:  # 3+ new paying customers
            create_business_event(
                db,
                'milestone_reached',
                f"💰 Crescita revenue: +{paying_growth} nuovi clienti paganti in 7 giorni!",
                metadata={'growth_period': '7_days', 'paying_growth': paying_growth}
            )
        
        if mrr_growth >= 20:  # €20+ MRR growth
            create_business_event(
                db,
                'milestone_reached',
                f"📈 MRR aumentato di €{mrr_growth:.2f} in 7 giorni!",
                metadata={'growth_period': '7_days', 'mrr_growth': mrr_growth}
            )
        
        logger.info(f"Growth analysis: customers +{customer_growth}, paying +{paying_growth}, MRR +€{mrr_growth:.2f}")
        
    except Exception as e:
        logger.error(f"Error in growth trend analysis: {e}")


def check_business_milestones(db):
    """
    Check for specific business milestones and create events
    """
    try:
        current_date = datetime.now(timezone.utc)
        
        # Check if today is a special date
        special_dates = {
            '01-01': '🎉 Nuovo Anno! Iniziamo alla grande!',
            '12-25': '🎄 Buon Natale dal team Chatello!',
            '07-04': '🇺🇸 Independence Day - mercato USA attivo!',
            '08-15': '🏖️ Ferragosto - picco traffico estivo',
            '11-29': '🛍️ Black Friday - opportunità sales!',
            '12-26': '💳 Boxing Day - continua lo shopping!'
        }
        
        date_key = current_date.strftime('%m-%d')
        if date_key in special_dates:
            create_business_event(
                db,
                'marketing_campaign',
                special_dates[date_key],
                metadata={'special_date': date_key}
            )
        
        # Check for week milestones
        if current_date.weekday() == 0:  # Monday
            create_business_event(
                db,
                'milestone_reached',
                '📊 Inizio nuova settimana - report settimanale',
                metadata={'week_start': current_date.strftime('%Y-%W')}
            )
        
        # Check for month milestones
        if current_date.day == 1:  # First day of month
            create_business_event(
                db,
                'milestone_reached',
                f'📅 Nuovo mese: {current_date.strftime("%B %Y")} - report mensile',
                metadata={'month_start': current_date.strftime('%Y-%m')}
            )
        
    except Exception as e:
        logger.error(f"Error checking business milestones: {e}")


def simulate_realistic_events(db):
    """
    Create realistic business events for demonstration
    (In production, this would be replaced by real webhook integrations)
    """
    try:
        import random
        
        # Get current stats to make realistic decisions
        total_customers = db.customers.count_documents({})
        active_licenses = db.licenses.count_documents({'status': 'active'})
        
        # Random chance for different events (adjust probabilities)
        events_to_create = []
        
        # Marketing events (30% chance)
        if random.random() < 0.3:
            marketing_events = [
                '📧 Newsletter inviata a 1,200+ subscribers',
                '📱 Post LinkedIn pubblicato - engagement alto',
                '🔍 Ottimizzazione SEO completata',
                '📺 Video tutorial pubblicato su YouTube',
                '🎯 Campagna Google Ads attivata',
                '📲 Aggiornamento social media strategy'
            ]
            events_to_create.append(('marketing_campaign', random.choice(marketing_events)))
        
        # Technical events (20% chance)
        if random.random() < 0.2:
            tech_events = [
                '🔧 Aggiornamento server completato',
                '🚀 Nuova feature in beta testing',
                '📊 Database performance ottimizzato',
                '🔒 Security audit completato',
                '☁️ Backup automatico verificato',
                '🔄 API response time migliorato del 15%'
            ]
            events_to_create.append(('feature_released', random.choice(tech_events)))
        
        # Customer support events (25% chance)
        if random.random() < 0.25:
            support_events = [
                '💬 5+ ticket risolti con valutazione 5/5',
                '📞 Chiamata onboarding nuovo cliente completata',
                '❓ FAQ aggiornate basate su feedback utenti',
                '🎯 Tutorial personalizzato creato per cliente enterprise',
                '📝 Documentazione API migliorata',
                '⚡ Tempo risposta support ridotto a <2h'
            ]
            events_to_create.append(('support_ticket', random.choice(support_events)))
        
        # Partnership events (10% chance)
        if random.random() < 0.1:
            partnership_events = [
                '🤝 Discussione partnership con azienda AI',
                '🌐 Integrazione con nuovo CMS in sviluppo',
                '📄 Contratto rivenditore in negoziazione',
                '🎪 Partecipazione evento tech confermata',
                '💼 Meeting con potenziale investitore'
            ]
            events_to_create.append(('partnership', random.choice(partnership_events)))
        
        # Create the selected events
        for event_type, description in events_to_create:
            create_business_event(
                db,
                event_type,
                description,
                metadata={'generated_by': 'daily_cron', 'realistic_simulation': True}
            )
            logger.info(f"Created simulated event: {event_type} - {description}")
        
    except Exception as e:
        logger.error(f"Error creating simulated events: {e}")


def run_daily_analytics():
    """
    Main function to run daily analytics collection
    """
    logger.info("🚀 Starting daily analytics cron job")
    
    try:
        # Connect to MongoDB
        mongo_client = MongoClient(MONGODB_URI)
        mongo_db = mongo_client[DATABASE_NAME]
        logger.info("✅ Connected to MongoDB Atlas")
        
        # Test connection
        mongo_client.admin.command('ping')
        logger.info("✅ MongoDB Atlas ping successful")
        
        # 1. Check and create milestones
        logger.info("📊 Checking for milestones...")
        check_and_create_milestones(mongo_db)
        
        # 2. Analyze growth trends
        logger.info("📈 Analyzing growth trends...")
        analyze_growth_trends(mongo_db)
        
        # 3. Check business milestones (special dates, etc.)
        logger.info("📅 Checking business milestones...")
        check_business_milestones(mongo_db)
        
        # 4. Create realistic business events for demo
        logger.info("🎲 Creating realistic business events...")
        simulate_realistic_events(mongo_db)
        
        # 5. Save today's analytics with all events
        logger.info("💾 Saving daily analytics with events...")
        result = save_daily_analytics_with_events(
            mongo_db,
            additional_notes="Dati raccolti automaticamente via cron job"
        )
        
        if result['success']:
            logger.info(f"✅ Daily analytics saved successfully!")
            logger.info(f"   📊 Total customers: {result['data']['total_customers']}")
            logger.info(f"   💰 Paying customers: {result['data']['paying_customers']}")
            logger.info(f"   💶 MRR: €{result['data']['mrr']}")
            logger.info(f"   📝 Events processed: {result['events_processed']}")
            logger.info(f"   🤖 Auto notes: {result['auto_notes']}")
        else:
            logger.error("❌ Failed to save daily analytics")
        
        # 6. Cleanup old events (keep last 90 days)
        cleanup_date = datetime.now(timezone.utc) - timedelta(days=90)
        cleanup_result = mongo_db.business_events.delete_many({
            'event_date': {'$lt': cleanup_date}
        })
        
        if cleanup_result.deleted_count > 0:
            logger.info(f"🗑️ Cleaned up {cleanup_result.deleted_count} old events")
        
        logger.info("🎉 Daily analytics cron job completed successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Daily analytics cron job failed: {e}")
        return False
    
    finally:
        if 'mongo_client' in locals():
            mongo_client.close()
            logger.info("🔐 MongoDB connection closed")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("📊 CHATELLO SAAS - DAILY ANALYTICS CRON JOB")
    logger.info("=" * 60)
    
    success = run_daily_analytics()
    
    if success:
        logger.info("✅ Cron job completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Cron job failed")
        sys.exit(1)