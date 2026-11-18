-- Generated from models.py (PostgreSQL). The app also creates these tables automatically on first start.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE airdrops (
	id UUID NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	description TEXT, 
	link_url VARCHAR(500) NOT NULL, 
	video_url VARCHAR(500), 
	is_active BOOLEAN, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE app_configs (
	id UUID NOT NULL, 
	config_key VARCHAR(100) NOT NULL, 
	config_value JSONB NOT NULL, 
	description TEXT, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (config_key)
);

CREATE TABLE banners (
	id UUID NOT NULL, 
	image_url VARCHAR(500) NOT NULL, 
	link_url VARCHAR(500), 
	is_active BOOLEAN, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE dashboard_widgets (
	id UUID NOT NULL, 
	widget_name VARCHAR(100) NOT NULL, 
	is_active BOOLEAN, 
	display_order INTEGER, 
	target_audience VARCHAR(50), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (widget_name)
);

CREATE TABLE subscription_plans (
	id UUID NOT NULL, 
	plan_name VARCHAR(50) NOT NULL, 
	price NUMERIC(10, 2) NOT NULL, 
	duration_days INTEGER NOT NULL, 
	features JSONB, 
	is_active BOOLEAN, 
	PRIMARY KEY (id)
);

CREATE TABLE trading_signals (
	id UUID NOT NULL, 
	pair VARCHAR(20) NOT NULL, 
	signal_type VARCHAR(10) NOT NULL, 
	entry_price NUMERIC(15, 4), 
	target_price NUMERIC(15, 4), 
	stop_loss NUMERIC(15, 4), 
	status VARCHAR(20), 
	created_at TIMESTAMP WITH TIME ZONE, 
	effectiveness_score INTEGER, 
	effectiveness_reason TEXT, 
	candle_pattern VARCHAR(100), 
	chart_pattern VARCHAR(100), 
	support_level NUMERIC(15, 4), 
	resistance_level NUMERIC(15, 4), 
	entry_zone VARCHAR(200), 
	analysis_details TEXT, 
	current_price NUMERIC(15, 4), 
	trailing_sl NUMERIC(15, 4), 
	position_size NUMERIC(10, 4), 
	regime VARCHAR(50), 
	rsi NUMERIC(10, 2), 
	reason VARCHAR(255), 
	sl_percent NUMERIC(10, 2), 
	tp_percent NUMERIC(10, 2), 
	votes_buy INTEGER, 
	votes_sell INTEGER, 
	votes_hold INTEGER, 
	PRIMARY KEY (id)
);

CREATE TABLE users (
	id UUID NOT NULL, 
	full_name VARCHAR(100) NOT NULL, 
	email VARCHAR(150) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role userrole, 
	is_verified BOOLEAN, 
	onboarding_step INTEGER, 
	is_active BOOLEAN, 
	avatar_url VARCHAR(255), 
	has_deposited BOOLEAN, 
	last_spin_at TIMESTAMP WITH TIME ZONE, 
	is_vip BOOLEAN, 
	auto_trade_active BOOLEAN, 
	referral_code VARCHAR(20), 
	referred_by UUID, 
	is_frozen BOOLEAN, 
	accepted_terms_at TIMESTAMP WITH TIME ZONE, 
	terms_version VARCHAR(20), 
	trading_consent BOOLEAN NOT NULL, 
	trading_consent_at TIMESTAMP WITH TIME ZONE, 
	trading_consent_version VARCHAR(20), 
	show_in_feed BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (referral_code), 
	FOREIGN KEY(referred_by) REFERENCES users (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE TABLE audit_logs (
	id UUID NOT NULL, 
	admin_id UUID, 
	admin_email VARCHAR(150), 
	action VARCHAR(60) NOT NULL, 
	target_type VARCHAR(40), 
	target_id VARCHAR(64), 
	before_value JSONB, 
	after_value JSONB, 
	reason VARCHAR(500), 
	ip_address VARCHAR(64), 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(admin_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);
CREATE INDEX ix_audit_logs_action ON audit_logs (action);
CREATE TABLE consent_logs (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	consent_type VARCHAR(30) NOT NULL, 
	action VARCHAR(10) NOT NULL, 
	version VARCHAR(20) NOT NULL, 
	ip_address VARCHAR(64), 
	user_agent VARCHAR(255), 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_consent_logs_user_id ON consent_logs (user_id);
CREATE TABLE notifications (
	id UUID NOT NULL, 
	user_id UUID, 
	title VARCHAR(255) NOT NULL, 
	message TEXT NOT NULL, 
	is_read BOOLEAN, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE support_tickets (
	id UUID NOT NULL, 
	user_id UUID, 
	subject VARCHAR(255), 
	status VARCHAR(20), 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE system_logs (
	id UUID NOT NULL, 
	user_id UUID, 
	error_type VARCHAR(100), 
	error_message TEXT, 
	device_info TEXT, 
	is_resolved BOOLEAN, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE transactions (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	amount NUMERIC(15, 2) NOT NULL, 
	transaction_type VARCHAR(50) NOT NULL, 
	status VARCHAR(20), 
	payment_gateway_id VARCHAR(100), 
	note VARCHAR(255), 
	meta JSONB, 
	reviewed_by UUID, 
	reviewed_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(reviewed_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE user_api_keys (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	exchange_name VARCHAR(50), 
	api_key_encrypted TEXT NOT NULL, 
	secret_key_encrypted TEXT NOT NULL, 
	is_active BOOLEAN, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE user_subscriptions (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	plan_id UUID, 
	start_date TIMESTAMP WITH TIME ZONE, 
	end_date TIMESTAMP WITH TIME ZONE, 
	is_active BOOLEAN, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(plan_id) REFERENCES subscription_plans (id)
);

CREATE TABLE wallets (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	real_balance NUMERIC(15, 2), 
	bonus_balance NUMERIC(15, 2), 
	spin_balance NUMERIC(15, 2), 
	total_earned NUMERIC(15, 2), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

