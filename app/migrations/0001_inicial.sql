-- EVSE Monitor · esquema inicial de D1 (SQLite).
-- Las horas son epoch UTC en segundos.

CREATE TABLE usuarios (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL UNIQUE COLLATE NOCASE,
  nombre TEXT NOT NULL,
  sal TEXT NOT NULL,
  hash TEXT NOT NULL,            -- sha256(sal:clave derivada en el navegador con PBKDF2)
  admin INTEGER NOT NULL DEFAULT 0,
  telegram_chat TEXT,
  creado INTEGER NOT NULL
);

CREATE TABLE sesiones_web (
  token_hash TEXT PRIMARY KEY,   -- sha256 del token de la cookie
  usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  expira INTEGER NOT NULL,
  creado INTEGER NOT NULL
);

CREATE TABLE intentos (            -- intentos fallidos de inicio de sesión (límite de 5 en 15 min)
  email TEXT NOT NULL,
  ts INTEGER NOT NULL
);
CREATE INDEX intentos_email ON intentos(email, ts);

CREATE TABLE equipos (
  id TEXT PRIMARY KEY,           -- p. ej. «evse-01»
  nombre TEXT NOT NULL,
  token_hash TEXT NOT NULL,      -- sha256 del secreto del equipo
  config TEXT NOT NULL DEFAULT '{}',
  config_v INTEGER NOT NULL DEFAULT 0,
  fw TEXT,
  mac TEXT,
  ultimo_contacto INTEGER,
  creado INTEGER NOT NULL
);

CREATE TABLE permisos (
  usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  equipo_id TEXT NOT NULL REFERENCES equipos(id) ON DELETE CASCADE,
  rol TEXT NOT NULL CHECK (rol IN ('propietario', 'lectura')),
  PRIMARY KEY (usuario_id, equipo_id)
);

CREATE TABLE mediciones (
  equipo_id TEXT NOT NULL,
  ts INTEGER NOT NULL,
  v REAL, i REAL, p REAL, pf REAL, f REAL,
  es REAL, et REAL,              -- kWh de la sesión y total
  tsn REAL, tam REAL, hum REAL,  -- sonda, ambiente, humedad
  k1 INTEGER, mot TEXT,
  PRIMARY KEY (equipo_id, ts)
) WITHOUT ROWID;

CREATE TABLE sesiones_carga (
  id INTEGER PRIMARY KEY,
  equipo_id TEXT NOT NULL,
  num INTEGER NOT NULL,
  inicio INTEGER NOT NULL,
  fin INTEGER,
  kwh REAL NOT NULL DEFAULT 0,
  p_max REAL,
  tarifa REAL,
  costo REAL,
  motivo_fin TEXT,
  UNIQUE (equipo_id, num, inicio)
);
CREATE INDEX sesiones_equipo ON sesiones_carga(equipo_id, inicio);

CREATE TABLE eventos (
  id INTEGER PRIMARY KEY,
  equipo_id TEXT NOT NULL,
  ts INTEGER NOT NULL,
  seq INTEGER NOT NULL,
  codigo TEXT NOT NULL,          -- arranque, k1, alarma, alarma_fin, sesion_inicio, limite, config, ...
  nivel INTEGER NOT NULL DEFAULT 0,  -- 0 info, 1 aviso, 2 alarma
  alarma TEXT,                   -- código de la alarma (temp_sonda, parar, ...)
  texto TEXT,
  valor REAL,
  extra INTEGER,
  mot TEXT,
  reconocido INTEGER NOT NULL DEFAULT 0,
  UNIQUE (equipo_id, seq, ts)
);
CREATE INDEX eventos_equipo ON eventos(equipo_id, ts);

CREATE TABLE ordenes (           -- bitácora de órdenes dadas desde la app
  id INTEGER PRIMARY KEY,
  equipo_id TEXT NOT NULL,
  usuario_id INTEGER,
  ts INTEGER NOT NULL,
  orden TEXT NOT NULL,
  args TEXT,
  ok INTEGER,
  msg TEXT
);
CREATE INDEX ordenes_equipo ON ordenes(equipo_id, ts);

CREATE TABLE firmware (
  version TEXT PRIMARY KEY,
  tam INTEGER NOT NULL,
  sha256 TEXT NOT NULL,
  notas TEXT,
  subido INTEGER NOT NULL
);
