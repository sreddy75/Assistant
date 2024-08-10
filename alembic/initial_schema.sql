Attempting to connect to: postgresql+psycopg://ai:ai@localhost:5532/ai
Successfully connected to the database.

Current Database Schema:
========================

Table: user_analytics

CREATE TABLE user_analytics (
	id SERIAL NOT NULL, 
	user_id VARCHAR, 
	event_type VARCHAR(50), 
	event_data JSON, 
	tools_used JSON, 
	delegated_assistant VARCHAR(100), 
	timestamp TIMESTAMP WITHOUT TIME ZONE, 
	duration DOUBLE PRECISION, 
	CONSTRAINT user_analytics_pkey PRIMARY KEY (id)
)



Table: user_2_documents

CREATE TABLE user_2_documents (
	id VARCHAR NOT NULL, 
	name VARCHAR, 
	meta_data JSONB DEFAULT '{}'::jsonb, 
	content TEXT, 
	embedding VECTOR(1536), 
	usage JSONB, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	content_hash VARCHAR, 
	user_id INTEGER, 
	CONSTRAINT user_2_documents_pkey PRIMARY KEY (id)
)



Table: votes

CREATE TABLE votes (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	query TEXT, 
	response TEXT, 
	is_upvote BOOLEAN, 
	sentiment_score DOUBLE PRECISION, 
	usefulness_rating INTEGER, 
	feedback_text TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	CONSTRAINT votes_pkey PRIMARY KEY (id)
)



Table: llm_os_runs

CREATE TABLE llm_os_runs (
	run_id VARCHAR NOT NULL, 
	name VARCHAR, 
	run_name VARCHAR, 
	user_id VARCHAR, 
	llm JSONB, 
	memory JSONB, 
	assistant_data JSONB, 
	run_data JSONB, 
	user_data JSONB, 
	task_data JSONB, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT llm_os_runs_pkey PRIMARY KEY (run_id)
)



Table: users

CREATE TABLE users (
	id SERIAL NOT NULL, 
	email VARCHAR, 
	hashed_password VARCHAR, 
	first_name VARCHAR, 
	last_name VARCHAR, 
	nickname VARCHAR, 
	role VARCHAR, 
	is_active BOOLEAN, 
	is_admin BOOLEAN, 
	trial_end TIMESTAMP WITH TIME ZONE, 
	email_verified BOOLEAN, 
	CONSTRAINT users_pkey PRIMARY KEY (id)
)



Table: user_1_documents

CREATE TABLE user_1_documents (
	id VARCHAR NOT NULL, 
	name VARCHAR, 
	meta_data JSONB DEFAULT '{}'::jsonb, 
	content TEXT, 
	embedding VECTOR(1536), 
	usage JSONB, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	content_hash VARCHAR, 
	user_id INTEGER, 
	CONSTRAINT user_1_documents_pkey PRIMARY KEY (id)
)



Table: alembic_version

CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL, 
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
)


