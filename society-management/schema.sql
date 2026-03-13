-- schema.sql
-- Run this once to set up the database.
-- mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS society_mgmt;
USE society_mgmt;

-- Users table (admin, guard, resident)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'guard', 'resident') NOT NULL DEFAULT 'resident',
    flat_number VARCHAR(20) DEFAULT NULL,
    block VARCHAR(10) DEFAULT NULL,
    phone VARCHAR(20) DEFAULT NULL,
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Visitors log
CREATE TABLE IF NOT EXISTS visitors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    visitor_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    visiting_flat VARCHAR(20) NOT NULL,
    visiting_block VARCHAR(10) DEFAULT NULL,
    purpose VARCHAR(255) DEFAULT NULL,
    otp VARCHAR(6) DEFAULT NULL,
    otp_verified TINYINT(1) DEFAULT 0,
    entry_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    exit_time DATETIME DEFAULT NULL,
    added_by INT,
    FOREIGN KEY (added_by) REFERENCES users(id)
);

-- Complaints
CREATE TABLE IF NOT EXISTS complaints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    resident_id INT NOT NULL,
    block VARCHAR(10) NOT NULL,
    flat_number VARCHAR(20) NOT NULL,
    category VARCHAR(50) DEFAULT 'General',
    description TEXT NOT NULL,
    status ENUM('Open', 'In Progress', 'Resolved', 'Closed') DEFAULT 'Open',
    admin_remarks TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (resident_id) REFERENCES users(id)
);

-- Parking slots
CREATE TABLE IF NOT EXISTS parking_slots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slot_label VARCHAR(10) NOT NULL UNIQUE,
    is_occupied TINYINT(1) DEFAULT 0,
    assigned_to INT DEFAULT NULL,
    vehicle_number VARCHAR(30) DEFAULT NULL,
    vehicle_type ENUM('Car', 'Bike', 'Other') DEFAULT 'Car',
    FOREIGN KEY (assigned_to) REFERENCES users(id)
);

-- Payments / maintenance bills
CREATE TABLE IF NOT EXISTS payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    resident_id INT NOT NULL,
    bill_period VARCHAR(30) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    due_date DATE NOT NULL,
    paid_on DATE DEFAULT NULL,
    status ENUM('Pending', 'Paid', 'Overdue') DEFAULT 'Pending',
    transaction_ref VARCHAR(100) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resident_id) REFERENCES users(id)
);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    target_role ENUM('all', 'admin', 'guard', 'resident') DEFAULT 'all',
    created_by INT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Seed some parking slots
INSERT IGNORE INTO parking_slots (slot_label) VALUES
('P-01'), ('P-02'), ('P-03'), ('P-04'), ('P-05'),
('P-06'), ('P-07'), ('P-08'), ('P-09'), ('P-10');
