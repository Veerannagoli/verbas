-- Verbas database (optional: app.py creates these tables automatically on start-up)
CREATE DATABASE IF NOT EXISTS verbas CHARACTER SET utf8mb4;
USE verbas;

CREATE TABLE IF NOT EXISTS contact_messages (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(190) NOT NULL,
    phone VARCHAR(40) NULL,
    company VARCHAR(160) NULL,
    service VARCHAR(120) NOT NULL,
    timeline VARCHAR(60) NULL,
    message TEXT NOT NULL,
    ip_address VARCHAR(64) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS whatsapp_enquiries (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    service VARCHAR(120) NULL,
    ip_address VARCHAR(64) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
