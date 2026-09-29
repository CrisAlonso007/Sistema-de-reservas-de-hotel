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
    imagen VARCHAR(500) NOT NULL DEFAULT '',
    mantenimiento TINYINT(1) NOT NULL DEFAULT 0,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- RESERVAS / ESTANCIAS
CREATE TABLE IF NOT EXISTS Reserva (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente VARCHAR(100) NOT NULL,
    identificacion VARCHAR(50) NOT NULL,
    contacto VARCHAR(50) NOT NULL,
    correo_electronico VARCHAR(255) NOT NULL DEFAULT '',
    noches INT NOT NULL,
    fecha_entrada DATE NOT NULL,
    fecha_salida DATE NOT NULL,
    metodo_pago ENUM('Tarjeta de Crédito / Débito', 'Efectivo en Recepción', 'Transferencia Bancaria') NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    estado ENUM('Pendiente', 'Confirmada', 'Iniciada', 'Finalizada', 'Cancelada') NOT NULL DEFAULT 'Pendiente',
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
    CONSTRAINT chk_reserva_total CHECK (total >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO Usuario
(username, passwrd, rol, nombre_completo, numero_identificacion, correo_electronico, numero_telefono, activo)
SELECT * FROM (
    SELECT 'recepcion' AS username,
        'pbkdf2_sha256$200000$5d4413d86e82e58dce5690c92c6f4a2f$4bf13249ee4bb9b0ac53293d7f4e14e78d47fe6ad3f2c771aa486b904c0321f3' AS passwrd,
        'recepcionista' AS rol,
        'Recepcionista Turno Día' AS nombre_completo,
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

-- ----------------------------------------------------------------------
-- CATALOGO INICIAL
-- ----------------------------------------------------------------------
INSERT INTO registro_habitacion (nombre, no_habitacion, tipo, precio, capacidad, descripcion)
SELECT * FROM (
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

-- RESERVAS DE EJEMPLO

INSERT INTO Reserva
(cliente, identificacion, contacto, correo_electronico, noches, fecha_entrada, fecha_salida,
 metodo_pago, total, estado, habitacion_id, empleado_id, checkin_empleado_id)
SELECT * FROM (
    SELECT 'Ana Torres Mendoza' AS cliente, 'CC-1020304050' AS identificacion, '310-555-1122' AS contacto,
        'ana.torres@example.com' AS correo_electronico, 3 AS noches,
        CURDATE() AS fecha_entrada, DATE_ADD(CURDATE(), INTERVAL 3 DAY) AS fecha_salida,
        'Tarjeta de Crédito / Débito' AS metodo_pago, 285.00 AS total, 'Iniciada' AS estado,
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 102) AS habitacion_id,
        (SELECT id FROM Usuario WHERE username = 'recepcion') AS empleado_id,
        (SELECT id FROM Usuario WHERE username = 'recepcion') AS checkin_empleado_id
    UNION ALL
    SELECT 'Luis Ramírez Peña', 'CC-5060708010', '311-777-3344', 'luis.ramirez@example.com', 2,
        CURDATE(), DATE_ADD(CURDATE(), INTERVAL 2 DAY),
        'Efectivo en Recepción', 260.00, 'Iniciada',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 103),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        (SELECT id FROM Usuario WHERE username = 'recepcion')
    UNION ALL
    SELECT 'María Gómez Silva', 'CC-9010203040', '312-888-5566', 'maria.gomez@example.com', 4,
        CURDATE(), DATE_ADD(CURDATE(), INTERVAL 4 DAY),
        'Transferencia Bancaria', 220.00, 'Pendiente',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 101),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        NULL
    UNION ALL
    SELECT 'Carlos Fernández Ruiz', 'CC-4050607080', '313-999-7788', 'carlos.fernandez@example.com', 1,
        DATE_ADD(CURDATE(), INTERVAL 1 DAY), DATE_ADD(CURDATE(), INTERVAL 2 DAY),
        'Tarjeta de Crédito / Débito', 55.00, 'Confirmada',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 104),
        (SELECT id FROM Usuario WHERE username = 'admin'),
        NULL
) AS semilla
WHERE NOT EXISTS (
    SELECT 1 FROM Reserva r
    WHERE r.habitacion_id = semilla.habitacion_id
    AND r.cliente = semilla.cliente
    AND r.fecha_entrada = semilla.fecha_entrada
    AND r.fecha_salida = semilla.fecha_salida
);
