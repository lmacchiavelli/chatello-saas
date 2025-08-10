-- Chatello SaaS Database Schema
-- Version: 1.0.0
-- Date: 2025-08-04

-- Create database
CREATE DATABASE IF NOT EXISTS chatello_saas;
USE chatello_saas;

-- Plans table (Starter, Pro, Agency)
CREATE TABLE IF NOT EXISTS plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'EUR',
    monthly_requests INT NOT NULL,
    max_sites INT NOT NULL DEFAULT 1,
    features JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    company VARCHAR(255),
    notes TEXT,
    phone VARCHAR(50),
    address TEXT,
    country VARCHAR(2),
    stripe_customer_id VARCHAR(255),
    paypal_customer_id VARCHAR(255),
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_status (status),
    INDEX idx_stripe (stripe_customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Licenses table
CREATE TABLE IF NOT EXISTS licenses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    license_key VARCHAR(64) NOT NULL UNIQUE,
    customer_id INT NOT NULL,
    plan_id INT NOT NULL,
    domain VARCHAR(255) NULL,
    status ENUM('active', 'inactive', 'suspended', 'expired') DEFAULT 'active',
    activated_at TIMESTAMP NULL,
    expires_at TIMESTAMP NULL,
    last_check TIMESTAMP NULL,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES plans(id),
    INDEX idx_license_key (license_key),
    INDEX idx_customer (customer_id),
    INDEX idx_status (status),
    INDEX idx_domain (domain),
    INDEX idx_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Usage logs table
CREATE TABLE IF NOT EXISTS usage_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    license_id INT NOT NULL,
    endpoint VARCHAR(50) NOT NULL,
    tokens_used INT DEFAULT 0,
    response_time_ms INT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE CASCADE,
    INDEX idx_license (license_id),
    INDEX idx_endpoint (endpoint),
    INDEX idx_created (created_at),
    INDEX idx_license_date (license_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Payments table
CREATE TABLE IF NOT EXISTS payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    license_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'EUR',
    status ENUM('pending', 'completed', 'failed', 'refunded') DEFAULT 'pending',
    payment_method VARCHAR(50),
    transaction_id VARCHAR(255),
    provider VARCHAR(50),
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE CASCADE,
    INDEX idx_customer (customer_id),
    INDEX idx_license (license_id),
    INDEX idx_status (status),
    INDEX idx_transaction (transaction_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- API Keys table (for storing encrypted provider keys)
CREATE TABLE IF NOT EXISTS api_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    api_key TEXT NOT NULL, -- Encrypted
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INT DEFAULT 0,
    last_used TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_provider (provider),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Activity logs table
CREATE TABLE IF NOT EXISTS activity_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    license_id INT,
    customer_id INT,
    action VARCHAR(100) NOT NULL,
    details JSON,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE SET NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
    INDEX idx_license (license_id),
    INDEX idx_customer (customer_id),
    INDEX idx_action (action),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert default plans
INSERT INTO plans (name, display_name, price, monthly_requests, max_sites, features) VALUES
('starter', 'Starter - BYOK', 2.99, 0, 1, '["bring_your_own_key", "1_site", "basic_support", "community_access"]'),
('pro', 'Pro - AI Inclusa', 7.99, 1000, 3, '["ai_included", "3_sites", "priority_support", "advanced_features", "no_api_key_needed"]'),
('agency', 'Agency - White Label', 19.99, 5000, -1, '["ai_included", "unlimited_sites", "white_label", "dedicated_support", "custom_branding", "api_access"]');

-- Create user for the Flask app
CREATE USER IF NOT EXISTS 'chatello_saas'@'localhost' IDENTIFIED BY 'ChatelloSaaS2025!';
GRANT ALL PRIVILEGES ON chatello_saas.* TO 'chatello_saas'@'localhost';
FLUSH PRIVILEGES;

-- Stored procedure to generate license key
DELIMITER $$
CREATE PROCEDURE IF NOT EXISTS generate_license_key(
    IN p_customer_id INT,
    IN p_plan_id INT,
    IN p_domain VARCHAR(255)
)
BEGIN
    DECLARE v_license_key VARCHAR(64);
    DECLARE v_exists INT DEFAULT 1;
    
    WHILE v_exists > 0 DO
        SET v_license_key = CONCAT(
            'CHA-',
            UPPER(SUBSTRING(MD5(RAND()), 1, 8)), '-',
            UPPER(SUBSTRING(MD5(RAND()), 1, 8)), '-',
            UPPER(SUBSTRING(MD5(RAND()), 1, 8)), '-',
            UPPER(SUBSTRING(MD5(RAND()), 1, 8))
        );
        
        SELECT COUNT(*) INTO v_exists FROM licenses WHERE license_key = v_license_key;
    END WHILE;
    
    INSERT INTO licenses (license_key, customer_id, plan_id, domain, status, activated_at)
    VALUES (v_license_key, p_customer_id, p_plan_id, p_domain, 'active', NOW());
    
    SELECT v_license_key AS license_key;
END$$
DELIMITER ;

-- Function to check usage limits
DELIMITER $$
CREATE FUNCTION IF NOT EXISTS check_usage_limit(
    p_license_id INT
) RETURNS BOOLEAN
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_requests_used INT;
    DECLARE v_requests_limit INT;
    
    SELECT COUNT(*) INTO v_requests_used
    FROM usage_logs
    WHERE license_id = p_license_id
    AND MONTH(created_at) = MONTH(CURRENT_DATE())
    AND YEAR(created_at) = YEAR(CURRENT_DATE());
    
    SELECT p.monthly_requests INTO v_requests_limit
    FROM licenses l
    JOIN plans p ON l.plan_id = p.id
    WHERE l.id = p_license_id;
    
    RETURN v_requests_used < v_requests_limit;
END$$
DELIMITER ;