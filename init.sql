-- Tabla de Usuarios
CREATE TABLE IF NOT EXISTS "Users" (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Agent',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de Acreedores (Bancos)
CREATE TABLE IF NOT EXISTS "Creditors" (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    abreviation TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de Afiliados
CREATE TABLE IF NOT EXISTS "Affiliates" (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    active BOOLEAN DEFAULT TRUE
);

-- Tabla de Logs (Notas)
CREATE TABLE IF NOT EXISTS "Logs" (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id INTEGER REFERENCES "Users"(id),
    agent TEXT NOT NULL,
    customer TEXT, -- Puede ser nulo por privacidad/censura
    cordoba_id TEXT NOT NULL,
    result TEXT NOT NULL,
    comments TEXT,
    affiliate TEXT,
    info_until TEXT,
    client_language TEXT
);

-- Tabla de Noticias (Updates)
CREATE TABLE IF NOT EXISTS "Updates" (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    category TEXT NOT NULL, -- 'Info', 'Warning', 'Critical'
    active BOOLEAN DEFAULT TRUE
);

-- USUARIO ADMIN POR DEFECTO
-- Username: admin
-- Password: admin1234(Hasheada con bcrypt para pruebas iniciales)
-- NOTA: Cambia este hash por uno generado por ti si quieres otra pass
INSERT INTO "Users" (username, name, password, role) 
VALUES ('admin', 'System Administrator', '$2b$12$VTtjK6Vlk4kAqWpvjF/SXu5suttIRYDE7vCx/WX9FudVWpUa6yZbi', 'Admin')
ON CONFLICT (username) DO NOTHING;

-- DATOS INICIALES DE EJEMPLO (Opcional)
INSERT INTO "Affiliates" (name) VALUES ('Patriot'), ('Cordoba Legal'), ('Titan') ON CONFLICT DO NOTHING;