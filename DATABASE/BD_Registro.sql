-- ======================================================================
-- CREDENCIALES INICIALES (cámbielas antes de usar el sistema):
--   usuario: recepcion / contrasena: recepcion2026   (recepcionista)
--   usuario: admin     / contrasena: admin2026       (administrador)
-- ======================================================================

CREATE DATABASE IF NOT EXISTS db_sistema_reserva
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE db_sistema_reserva;

-- PERSONAL DEL HOTEL (recepcionistas y administradores)
CREATE TABLE IF NOT EXISTS Usuario (  
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    passwrd VARCHAR(255) NOT NULL,
    rol ENUM('recepcionista', 'administrador') NOT NULL DEFAULT 'recepcionista',
    nombre_completo VARCHAR(150) NOT NULL,
    numero_identificacion VARCHAR(50) NOT NULL UNIQUE,
    correo_electronico VARCHAR(255) NOT NULL UNIQUE,
    numero_telefono VARCHAR(50) NOT NULL UNIQUE,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_usuario_rol (rol, activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- CATALOGO DE HABITACIONES
CREATE TABLE IF NOT EXISTS registro_habitacion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    no_habitacion INT NOT NULL UNIQUE,
    tipo ENUM('Simple', 'Doble', 'Matrimonial', 'Suite', 'Deluxe', 'Presidencial') NOT NULL DEFAULT 'Simple',
    precio DECIMAL(10,2) NOT NULL,
    capacidad INT NOT NULL DEFAULT 2,
    descripcion VARCHAR(255) NOT NULL,
    imagen VARCHAR(500) NOT NULL DEFAULT 'recursos/placeholder-image.jpg',
    mantenimiento TINYINT(1) NOT NULL DEFAULT 0,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE registro_habitacion
    MODIFY COLUMN imagen VARCHAR(500) NOT NULL DEFAULT 'recursos/placeholder-image.jpg';

UPDATE registro_habitacion
SET imagen = 'recursos/placeholder-image.jpg'
WHERE id > 0
  AND (
      imagen IS NULL
      OR imagen = ''
      OR imagen = 'recursos/placeholder-image.png'
  );

-- RESERVAS / ESTANCIAS
CREATE TABLE IF NOT EXISTS Reserva (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente VARCHAR(100) NOT NULL,
    identificacion VARCHAR(50) NOT NULL,
    contacto VARCHAR(50) NOT NULL,
    numero_huespedes INT NOT NULL DEFAULT 1,
    noches INT NOT NULL,
    fecha_entrada DATE NOT NULL,
    fecha_salida DATE NOT NULL,
    metodo_pago ENUM('Tarjeta de Crédito / Débito', 'Efectivo en Recepción', 'Transferencia Bancaria') NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    monto_pagado DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    estado ENUM('Pendiente', 'Iniciada', 'Finalizada', 'Cancelada', 'No presentada') NOT NULL DEFAULT 'Pendiente',
    habitacion_id INT NOT NULL,
    empleado_id INT NOT NULL,
    checkin_empleado_id INT NULL,
    salida_empleado_id INT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (habitacion_id) REFERENCES registro_habitacion(id) ON DELETE RESTRICT,
    FOREIGN KEY (empleado_id) REFERENCES Usuario(id) ON DELETE RESTRICT,
    FOREIGN KEY (checkin_empleado_id) REFERENCES Usuario(id) ON DELETE SET NULL,
    FOREIGN KEY (salida_empleado_id) REFERENCES Usuario(id) ON DELETE SET NULL,
    INDEX idx_reserva_disponibilidad (habitacion_id, estado, fecha_entrada, fecha_salida),
    INDEX idx_reserva_recepcion (estado, fecha_entrada),
    INDEX idx_reserva_empleado (empleado_id),
    CONSTRAINT chk_reserva_fechas CHECK (fecha_salida > fecha_entrada),
    CONSTRAINT chk_reserva_noches CHECK (noches > 0),
    CONSTRAINT chk_reserva_numero_huespedes CHECK (numero_huespedes > 0),
    CONSTRAINT chk_reserva_total CHECK (total >= 0),
    CONSTRAINT chk_reserva_monto_pagado CHECK (monto_pagado >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE Reserva
    MODIFY COLUMN estado
        ENUM('Pendiente', 'Iniciada', 'Finalizada', 'Cancelada', 'No presentada')
        NOT NULL DEFAULT 'Pendiente';

-- Compatibilidad con instalaciones anteriores: agrega el campo sin reemplazar
-- reservas existentes (que quedan con 1 huésped como valor predeterminado).
SET @existe_numero_huespedes = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'Reserva'
      AND column_name = 'numero_huespedes'
);
SET @sql_migracion_huespedes = IF(
    @existe_numero_huespedes = 0,
    'ALTER TABLE Reserva ADD COLUMN numero_huespedes INT NOT NULL DEFAULT 1, '
    'ADD CONSTRAINT chk_reserva_numero_huespedes CHECK (numero_huespedes > 0)',
    'SELECT 1'
);
PREPARE migracion_huespedes FROM @sql_migracion_huespedes;
EXECUTE migracion_huespedes;
DEALLOCATE PREPARE migracion_huespedes;

-- TAREAS DE LIMPIEZA Y MANTENIMIENTO, con inicio y fin reales del servicio.
CREATE TABLE IF NOT EXISTS TareaHabitacion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    habitacion_id INT NOT NULL,
    reserva_id INT NULL,
    tipo ENUM('Limpieza diaria', 'Limpieza de salida', 'Mantenimiento técnico') NOT NULL,
    turno ENUM('Mañana', 'Tarde', 'Salida', 'Mantenimiento') NOT NULL,
    fecha_programada DATE NOT NULL,
    estado ENUM('Pendiente', 'En proceso', 'Completada', 'Cancelada')
        NOT NULL DEFAULT 'Pendiente',
    iniciada_en DATETIME NULL,
    finalizada_en DATETIME NULL,
    iniciada_por INT NULL,
    finalizada_por INT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (habitacion_id) REFERENCES registro_habitacion(id) ON DELETE RESTRICT,
    FOREIGN KEY (reserva_id) REFERENCES Reserva(id) ON DELETE SET NULL,
    FOREIGN KEY (iniciada_por) REFERENCES Usuario(id) ON DELETE SET NULL,
    FOREIGN KEY (finalizada_por) REFERENCES Usuario(id) ON DELETE SET NULL,
    UNIQUE KEY uq_tarea_reserva_turno (reserva_id, tipo, fecha_programada, turno),
    INDEX idx_tarea_estado_fecha (estado, fecha_programada),
    INDEX idx_tarea_habitacion (habitacion_id, tipo, estado, fecha_programada)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- COBROS / PAGOS DE UNA ESTANCIA
CREATE TABLE IF NOT EXISTS Pago (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reserva_id INT NOT NULL,
    monto DECIMAL(10,2) NOT NULL,
    metodo_pago ENUM('Tarjeta de Crédito / Débito', 'Efectivo en Recepción', 'Transferencia Bancaria') NOT NULL,
    empleado_id INT NOT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reserva_id) REFERENCES Reserva(id) ON DELETE CASCADE,
    FOREIGN KEY (empleado_id) REFERENCES Usuario(id) ON DELETE RESTRICT,
    INDEX idx_pago_reserva (reserva_id),
    CONSTRAINT chk_pago_monto CHECK (monto > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Devoluciones trazables: nunca se borra un cobro original.
CREATE TABLE IF NOT EXISTS Devolucion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reserva_id INT NOT NULL,
    empleado_id INT NOT NULL,
    monto DECIMAL(10,2) NOT NULL,
    motivo VARCHAR(255) NOT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reserva_id) REFERENCES Reserva(id) ON DELETE RESTRICT,
    FOREIGN KEY (empleado_id) REFERENCES Usuario(id) ON DELETE RESTRICT,
    INDEX idx_devolucion_reserva (reserva_id),
    CONSTRAINT chk_devolucion_monto CHECK (monto > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Contador transaccional para emitir numeración consecutiva sin duplicados.
CREATE TABLE IF NOT EXISTS ControlComprobante (
    id TINYINT PRIMARY KEY,
    siguiente INT UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO ControlComprobante (id, siguiente) VALUES (1, 1);

CREATE TABLE IF NOT EXISTS Comprobante (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pago_id INT NOT NULL UNIQUE,
    numero VARCHAR(40) NOT NULL UNIQUE,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pago_id) REFERENCES Pago(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- PARAMETROS DEL HOTEL Y TARIFAS
CREATE TABLE IF NOT EXISTS Configuracion (
    clave VARCHAR(60) PRIMARY KEY,
    valor VARCHAR(1000) NOT NULL,
    descripcion VARCHAR(255) NOT NULL DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE Configuracion
    MODIFY COLUMN valor VARCHAR(1000) NOT NULL;

CREATE TABLE IF NOT EXISTS Devolucion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reserva_id INT NOT NULL,
    empleado_id INT NOT NULL,
    monto DECIMAL(10,2) NOT NULL,
    motivo VARCHAR(255) NOT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reserva_id) REFERENCES Reserva(id) ON DELETE RESTRICT,
    FOREIGN KEY (empleado_id) REFERENCES Usuario(id) ON DELETE RESTRICT,
    INDEX idx_devolucion_reserva (reserva_id),
    CONSTRAINT chk_devolucion_monto CHECK (monto > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ControlComprobante (
    id TINYINT PRIMARY KEY,
    siguiente INT UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO ControlComprobante (id, siguiente) VALUES (1, 1);

CREATE TABLE IF NOT EXISTS Comprobante (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pago_id INT NOT NULL UNIQUE,
    numero VARCHAR(40) NOT NULL UNIQUE,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pago_id) REFERENCES Pago(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Verificacion: deben aparecer Devolucion, Comprobante y ControlComprobante.
SELECT TABLE_NAME
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name IN ('Devolucion', 'Comprobante', 'ControlComprobante')
ORDER BY TABLE_NAME;

-- ======================================================================
-- DATOS ESENCIALES (Configuración, Usuarios base y Habitaciones base)
-- ======================================================================

INSERT INTO Configuracion (clave, valor, descripcion) VALUES
    ('hotel_nombre', 'Allogi Hotel', 'Nombre del hotel'),
    ('hotel_direccion', '', 'Dirección del hotel'),
    ('hotel_telefono', '', 'Teléfono del hotel'),
    ('hotel_correo', '', 'Correo del hotel'),
    ('hora_checkin', '14:00', 'Hora habitual de check-in'),
    ('hora_checkout', '12:00', 'Hora habitual de check-out'),
    ('horario_recepcion', '24 horas', 'Horario de atención de recepción'),
    ('confirmacion_horas', '0', 'Horas para confirmar; 0 significa sin vencimiento automático'),
    ('cancelacion_horas_limite', '48', 'Horas antes del check-in para cancelar sin penalización'),
    ('cancelacion_penalizacion_pct', '20', 'Porcentaje retenido por cancelación tardía'),
    ('no_show_penalizacion_pct', '30', 'Porcentaje retenido en caso de no-show'),
    ('late_checkout_hora', '14:00', 'Hora límite para late check-out'),
    ('late_checkout_cargo', '0.00', 'Cargo por late check-out; 0 significa sin cargo'),
    ('moneda', 'NIO', 'Moneda principal: NIO o USD'),
    ('metodos_pago', '["Tarjeta de Crédito / Débito","Efectivo en Recepción","Transferencia Bancaria"]', 'Métodos de pago aceptados en formato JSON'),
    ('comprobante_prefijo', 'COMP', 'Prefijo de la numeración de comprobantes'),
    ('comprobante_mensaje', 'Gracias por su preferencia.', 'Nota al pie de los comprobantes')
ON DUPLICATE KEY UPDATE clave = clave;

INSERT INTO Usuario
(username, passwrd, rol, nombre_completo, numero_identificacion, correo_electronico, numero_telefono, activo)
SELECT username, passwrd, rol, nombre_completo, numero_identificacion, correo_electronico, numero_telefono, activo
FROM (
    SELECT 'recepcion' AS username,
        'pbkdf2_sha256$200000$5d4413d86e82e58dce5690c92c6f4a2f$4bf13249ee4bb9b0ac53293d7f4e14e78d47fe6ad3f2c771aa486b904c0321f3' AS passwrd,
        'recepcionista' AS rol,
        'Recepcionista' AS nombre_completo,
        'EMP-0001' AS numero_identificacion,
        'recepcion@hotel.local' AS correo_electronico,
        '300-111-2233' AS numero_telefono,
        1 AS activo
    UNION ALL
    SELECT 'admin',
        'pbkdf2_sha256$200000$dc42d30969a370a67d0270be4a45bf96$83cd1c4c2bd9690cbe174404f3d9c28a727da0163ea7f84f931d445c510156f5',
        'administrador',
        'Administrador del Hotel',
        'EMP-0002',
        'admin@hotel.local',
        '300-222-4455',
        1
) AS semilla
WHERE NOT EXISTS (
    SELECT 1 FROM Usuario u WHERE u.username = semilla.username
);

INSERT INTO registro_habitacion (nombre, no_habitacion, tipo, precio, capacidad, descripcion)
SELECT nombre, no_habitacion, tipo, precio, capacidad, descripcion
FROM (
    SELECT 'Suite Presidencial Vista al Mar' AS nombre, 101 AS no_habitacion, 'Suite' AS tipo, 150.00 AS precio, 2 AS capacidad,
        'Cama King Size, jacuzzi privado, vista panorámica al mar y servicio a la habitación 24/7.' AS descripcion
    UNION ALL
    SELECT 'Habitación Doble Clásica', 102, 'Doble', 80.00, 2,
        'Dos camas individuales, escritorio de trabajo, aire acondicionado y baño privado.'
    UNION ALL
    SELECT 'Habitación Matrimonial', 103, 'Matrimonial', 95.00, 2,
        'Cama matrimonial, lamparitas, minibar y ropa de cama de primera calidad.'
    UNION ALL
    SELECT 'Habitación Simple Económica', 104, 'Simple', 55.00, 1,
        'Cama individual, escritorio, televisión y baño privado con ducha.'
    UNION ALL
    SELECT 'Habitación Deluxe Panorámica', 201, 'Deluxe', 130.00, 3,
        'Habitación amplia con terraza privada, sofá cama y desayuno incluido.'
) AS semilla
WHERE NOT EXISTS (
    SELECT 1 FROM registro_habitacion h WHERE h.no_habitacion = semilla.no_habitacion
);
