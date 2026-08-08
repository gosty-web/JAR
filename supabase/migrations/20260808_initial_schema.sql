-- Initial Schema for JAR Long-Term Memory and Skills

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: long_term_memory
CREATE TABLE IF NOT EXISTS long_term_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    memory_type VARCHAR(50) NOT NULL, -- e.g., 'preference', 'contact', 'workflow'
    content TEXT NOT NULL,
    context_tags TEXT[]
);

-- Table: skills
CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    version INTEGER DEFAULT 1,
    code_body TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true
);

-- Table: session_logs
CREATE TABLE IF NOT EXISTS session_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    session_id UUID NOT NULL,
    task_description TEXT NOT NULL,
    status VARCHAR(50) NOT NULL, -- 'success', 'failed', 'needs_user'
    failure_reason TEXT
);
