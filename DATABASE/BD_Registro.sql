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
    noches INT NOT NULL,
    fecha_entrada DATE NOT NULL,
    fecha_salida DATE NOT NULL,
    metodo_pago ENUM('Tarjeta de Crédito / Débito', 'Efectivo en Recepción', 'Transferencia Bancaria') NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    monto_pagado DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    estado ENUM('Pendiente', 'Iniciada', 'Finalizada', 'Cancelada') NOT NULL DEFAULT 'Pendiente',
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
    CONSTRAINT chk_reserva_total CHECK (total >= 0),
    CONSTRAINT chk_reserva_monto_pagado CHECK (monto_pagado >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Las reservas confirmadas se integran a Pendiente y se retira ese estado
-- del ENUM, también en bases existentes que vuelvan a ejecutar este script.
UPDATE Reserva
SET estado = 'Pendiente'
WHERE CAST(estado AS CHAR) = 'Confirmada';
ALTER TABLE Reserva
    MODIFY COLUMN estado ENUM('Pendiente', 'Iniciada', 'Finalizada', 'Cancelada')
    NOT NULL DEFAULT 'Pendiente';

-- COBROS / PAGOS DE UNA ESTANCIA
-- Cada fila es un abono. `Reserva.monto_pagado` es su caché (suma de los
-- abonos) y se mantiene dentro de la misma transacción que inserta el pago.
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

-- PARAMETROS DEL HOTEL Y TARIFAS
-- Configuración clave-valor editable por el administrador: antelación y
-- duración de las estancias, temporada alta y descuentos. Se guarda como texto
-- y cada servicio la interpreta, para no tener que agregar columnas cuando
-- aparezca un parámetro nuevo.
CREATE TABLE IF NOT EXISTS Configuracion (
    clave VARCHAR(60) PRIMARY KEY,
    valor VARCHAR(255) NOT NULL,
    descripcion VARCHAR(255) NOT NULL DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO Configuracion (clave, valor, descripcion) VALUES
    ('dias_anticipacion_max', '90', 'Antelación máxima, en días, con la que se puede reservar'),
    ('noches_minimas', '1', 'Número mínimo de noches por estancia'),
    ('noches_maximas', '30', 'Número máximo de noches por estancia'),
    ('temporada_alta_inicio', '', 'Primer día de temporada alta (YYYY-MM-DD; vacío = sin temporada)'),
    ('temporada_alta_fin', '', 'Último día de temporada alta (YYYY-MM-DD)'),
    ('factor_temporada_alta', '1.20', 'Recargo aplicado al precio por noche en temporada alta'),
    ('descuento_porcentaje', '0', 'Descuento general aplicado al total de la estancia (%)'),
    ('dias_aviso_pago', '3', 'Días de antelación con que se avisa un cobro pendiente')
ON DUPLICATE KEY UPDATE clave = clave;

INSERT INTO Usuario
(username, passwrd, rol, nombre_completo, numero_identificacion, correo_electronico, numero_telefono, activo)
SELECT * FROM (
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
(cliente, identificacion, contacto, noches, fecha_entrada, fecha_salida,
 metodo_pago, total, estado, habitacion_id, empleado_id, checkin_empleado_id)
SELECT * FROM (
    SELECT 'Ana Torres Mendoza' AS cliente, 'CC-1020304050' AS identificacion, '310-555-1122' AS contacto, 3 AS noches,
        CURDATE() AS fecha_entrada, DATE_ADD(CURDATE(), INTERVAL 3 DAY) AS fecha_salida,
        'Tarjeta de Crédito / Débito' AS metodo_pago, 285.00 AS total, 'Iniciada' AS estado,
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 102) AS habitacion_id,
        (SELECT id FROM Usuario WHERE username = 'recepcion') AS empleado_id,
        (SELECT id FROM Usuario WHERE username = 'recepcion') AS checkin_empleado_id
    UNION ALL
    SELECT 'Luis Ramírez Peña', 'CC-5060708010', '311-777-3344', 2,
        CURDATE(), DATE_ADD(CURDATE(), INTERVAL 2 DAY),
        'Efectivo en Recepción', 260.00, 'Iniciada',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 103),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        (SELECT id FROM Usuario WHERE username = 'recepcion')
    UNION ALL
    SELECT 'María Gómez Silva', 'CC-9010203040', '312-888-5566', 4,
        CURDATE(), DATE_ADD(CURDATE(), INTERVAL 4 DAY),
        'Transferencia Bancaria', 220.00, 'Pendiente',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 101),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        NULL
    UNION ALL
    SELECT 'Carlos Fernández Ruiz', 'CC-4050607080', '313-999-7788', 1,
        DATE_ADD(CURDATE(), INTERVAL 1 DAY), DATE_ADD(CURDATE(), INTERVAL 2 DAY),
        'Tarjeta de Crédito / Débito', 55.00, 'Pendiente',
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

-- ======================================================================
-- REGISTRO DE RESERVAS DE EJEMPLO (4 POR CADA UNO DE LOS 4 ESTADOS)
-- Sin columna 'correo_electronico' y sin estado 'Confirmada'
-- ======================================================================

INSERT INTO Reserva (
    cliente, identificacion, contacto, noches, 
    fecha_entrada, fecha_salida, metodo_pago, total, estado, 
    habitacion_id, empleado_id, checkin_empleado_id, salida_empleado_id
) 
SELECT * FROM (

    -- ------------------------------------------------------------------
    -- 1. ESTADO: PENDIENTE (4 Reservas futuras)
    -- ------------------------------------------------------------------
    SELECT 
        'Carlos Mendoza Ruiz' AS cliente, 'CC-10101010' AS identificacion, '300-111-0001' AS contacto,
        3 AS noches, DATE_ADD(CURDATE(), INTERVAL 5 DAY) AS fecha_entrada, DATE_ADD(CURDATE(), INTERVAL 8 DAY) AS fecha_salida,
        'Tarjeta de Crédito / Débito' AS metodo_pago, 450.00 AS total, 'Pendiente' AS estado,
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 101) AS habitacion_id,
        (SELECT id FROM Usuario WHERE username = 'recepcion') AS empleado_id,
        NULL AS checkin_empleado_id, NULL AS salida_empleado_id

    UNION ALL SELECT 
        'Sofía López Vargas', 'CC-10101011', '300-111-0002',
        2, DATE_ADD(CURDATE(), INTERVAL 10 DAY), DATE_ADD(CURDATE(), INTERVAL 12 DAY),
        'Efectivo en Recepción', 160.00, 'Pendiente',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 102),
        (SELECT id FROM Usuario WHERE username = 'recepcion'), NULL, NULL

    UNION ALL SELECT 
        'Andrés Castro Silva', 'CC-10101012', '300-111-0003',
        4, DATE_ADD(CURDATE(), INTERVAL 15 DAY), DATE_ADD(CURDATE(), INTERVAL 19 DAY),
        'Transferencia Bancaria', 520.00, 'Pendiente',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 201),
        (SELECT id FROM Usuario WHERE username = 'recepcion'), NULL, NULL

    UNION ALL SELECT 
        'Mariana Gómez Paz', 'CC-10101013', '300-111-0004',
        1, DATE_ADD(CURDATE(), INTERVAL 2 DAY), DATE_ADD(CURDATE(), INTERVAL 3 DAY),
        'Tarjeta de Crédito / Débito', 60.00, 'Pendiente',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 205),
        (SELECT id FROM Usuario WHERE username = 'recepcion'), NULL, NULL

    -- ------------------------------------------------------------------
    -- 2. ESTADO: INICIADA (4 Huéspedes alojados actualmente)
    -- ------------------------------------------------------------------
    UNION ALL SELECT 
        'Juan Pablo Duarte', 'CC-30303010', '300-333-0001',
        3, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 3 DAY),
        'Tarjeta de Crédito / Débito', 255.00, 'Iniciada',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 202),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        (SELECT id FROM Usuario WHERE username = 'recepcion'), NULL

    UNION ALL SELECT 
        'Valeria Marín Delgado', 'CC-30303011', '300-333-0002',
        2, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 2 DAY),
        'Efectivo en Recepción', 280.00, 'Iniciada',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 203),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        (SELECT id FROM Usuario WHERE username = 'recepcion'), NULL

    UNION ALL SELECT 
        'Roberto Ortega Núñez', 'CC-30303012', '300-333-0003',
        4, DATE_SUB(CURDATE(), INTERVAL 1 DAY), DATE_ADD(CURDATE(), INTERVAL 3 DAY),
        'Transferencia Bancaria', 540.00, 'Iniciada',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 302),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        (SELECT id FROM Usuario WHERE username = 'recepcion'), NULL

    UNION ALL SELECT 
        'Elena Benítez Castillo', 'CC-30303013', '300-333-0004',
        2, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 2 DAY),
        'Tarjeta de Crédito / Débito', 440.00, 'Iniciada',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 402),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        (SELECT id FROM Usuario WHERE username = 'recepcion'), NULL

    -- ------------------------------------------------------------------
    -- 3. ESTADO: FINALIZADA (4 Estancias concluidas / Check-out)
    -- ------------------------------------------------------------------
    UNION ALL SELECT 
        'Diego Paredes Acosta', 'CC-40404010', '300-444-0001',
        2, DATE_SUB(CURDATE(), INTERVAL 5 DAY), DATE_SUB(CURDATE(), INTERVAL 3 DAY),
        'Efectivo en Recepción', 110.00, 'Finalizada',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 104),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        (SELECT id FROM Usuario WHERE username = 'recepcion')

    UNION ALL SELECT 
        'Claudia Espinoza Gil', 'CC-40404011', '300-444-0002',
        3, DATE_SUB(CURDATE(), INTERVAL 7 DAY), DATE_SUB(CURDATE(), INTERVAL 4 DAY),
        'Tarjeta de Crédito / Débito', 300.00, 'Finalizada',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 204),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        (SELECT id FROM Usuario WHERE username = 'recepcion')

    UNION ALL SELECT 
        'Hugo Santamaría Reyes', 'CC-40404012', '300-444-0003',
        1, DATE_SUB(CURDATE(), INTERVAL 2 DAY), DATE_SUB(CURDATE(), INTERVAL 1 DAY),
        'Transferencia Bancaria', 65.00, 'Finalizada',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 305),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        (SELECT id FROM Usuario WHERE username = 'recepcion')

    UNION ALL SELECT 
        'Beatriz Roldán Marín', 'CC-40404013', '300-444-0004',
        2, DATE_SUB(CURDATE(), INTERVAL 4 DAY), DATE_SUB(CURDATE(), INTERVAL 2 DAY),
        'Tarjeta de Crédito / Débito', 360.00, 'Finalizada',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 401),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        (SELECT id FROM Usuario WHERE username = 'recepcion')

    -- ------------------------------------------------------------------
    -- 4. ESTADO: CANCELADA (4 Reservas anuladas antes de la entrada)
    -- ------------------------------------------------------------------
    UNION ALL SELECT 
        'Javier Salazar Meza', 'CC-50505010', '300-555-0001',
        2, DATE_ADD(CURDATE(), INTERVAL 1 DAY), DATE_ADD(CURDATE(), INTERVAL 3 DAY),
        'Efectivo en Recepción', 100.00, 'Cancelada',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 105),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        NULL,
        (SELECT id FROM Usuario WHERE username = 'recepcion')

    UNION ALL SELECT 
        'Natalia Franco Cárdenas', 'CC-50505011', '300-555-0002',
        3, DATE_ADD(CURDATE(), INTERVAL 8 DAY), DATE_ADD(CURDATE(), INTERVAL 11 DAY),
        'Transferencia Bancaria', 270.00, 'Cancelada',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 303),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        NULL,
        (SELECT id FROM Usuario WHERE username = 'recepcion')

    UNION ALL SELECT 
        'Patricia Zambrano Ponce', 'CC-50505012', '300-555-0003',
        2, DATE_ADD(CURDATE(), INTERVAL 12 DAY), DATE_ADD(CURDATE(), INTERVAL 14 DAY),
        'Tarjeta de Crédito / Débito', 220.00, 'Cancelada',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 304),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        NULL,
        (SELECT id FROM Usuario WHERE username = 'recepcion')

    UNION ALL SELECT 
        'Gonzalo Ibáñez Vela', 'CC-50505013', '300-555-0004',
        1, DATE_ADD(CURDATE(), INTERVAL 6 DAY), DATE_ADD(CURDATE(), INTERVAL 7 DAY),
        'Efectivo en Recepción', 90.00, 'Cancelada',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 404),
        (SELECT id FROM Usuario WHERE username = 'recepcion'),
        NULL,
        (SELECT id FROM Usuario WHERE username = 'recepcion')

) AS semilla
WHERE NOT EXISTS (
    SELECT 1 FROM Reserva r 
    WHERE r.habitacion_id = semilla.habitacion_id 
      AND r.cliente = semilla.cliente 
      AND r.fecha_entrada = semilla.fecha_entrada
);

INSERT INTO Reserva (
    cliente, identificacion, contacto, noches, 
    fecha_entrada, fecha_salida, metodo_pago, total, estado, 
    habitacion_id, empleado_id, checkin_empleado_id, salida_empleado_id
) 
SELECT * FROM (
    SELECT 
        'Valeria Gómez Castro' AS cliente, 'CC-1098765432' AS identificacion, '300-888-0001' AS contacto,
        3 AS noches, CURDATE() AS fecha_entrada, DATE_ADD(CURDATE(), INTERVAL 3 DAY) AS fecha_salida,
        'Tarjeta de Crédito / Débito' AS metodo_pago, 450.00 AS total, 'Pendiente' AS estado,
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 101) AS habitacion_id,
        (SELECT id FROM Usuario WHERE username = 'recepcion') AS empleado_id,
        NULL AS checkin_empleado_id, NULL AS salida_empleado_id

    UNION ALL SELECT 
        'Mateo Fernández Vega', 'CC-1098765433', '300-888-0002',
        2, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 2 DAY),
        'Efectivo en Recepción', 160.00, 'Pendiente',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 102),
        (SELECT id FROM Usuario WHERE username = 'recepcion'), NULL, NULL

    UNION ALL SELECT 
        'Camila Restrepo Silva', 'CC-1098765434', '300-888-0003',
        4, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 4 DAY),
        'Transferencia Bancaria', 520.00, 'Pendiente',
        (SELECT id FROM registro_habitacion WHERE no_habitacion = 201),
        (SELECT id FROM Usuario WHERE username = 'recepcion'), NULL, NULL
) AS semilla
WHERE NOT EXISTS (
    SELECT 1 FROM Reserva r 
    WHERE r.habitacion_id = semilla.habitacion_id 
      AND r.cliente = semilla.cliente 
      AND r.fecha_entrada = semilla.fecha_entrada
);