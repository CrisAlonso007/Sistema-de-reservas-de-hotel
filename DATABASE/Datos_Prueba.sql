-- Datos de simulacion para el Sistema de Reservas de Hotel.
-- Ejecutar DESPUES de DATABASE/BD_Registro.sql, en db_sistema_reserva.
-- Los nombres son ficticios pero realistas; no corresponden a personas reales.
-- Las habitaciones 9001-9020 y documentos SIM-2026-xxxx se reservan para
-- identificar este conjunto y evitar confundirlo con huéspedes reales.
-- No elimina registros. Al volver a ejecutarse actualiza los registros de
-- simulacion anteriores y no duplica habitaciones, reservas, pagos ni tareas.
--
-- Acceso con las cuentas iniciales del esquema:
--   Recepcionista: recepcion / recepcion2026
--   Administrador: admin / admin2026
--
-- Las fechas relativas a CURDATE() mantienen vigentes los escenarios.

USE db_sistema_reserva;

-- Algunas instalaciones anteriores no tienen estas tablas financieras.
-- Se crean solo si faltan; no se modifican pagos ni comprobantes existentes.
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

START TRANSACTION;

-- Habitaciones adicionales para explorar disponibilidad, capacidad, catálogo
-- y mantenimiento sin reutilizar las habitaciones base del esquema.
INSERT INTO registro_habitacion
    (nombre, no_habitacion, tipo, precio, capacidad, descripcion, mantenimiento)
SELECT datos.nombre, datos.no_habitacion, datos.tipo, datos.precio,
       datos.capacidad, datos.descripcion, datos.mantenimiento
FROM (
    SELECT 'Habitación Doble Jardín' AS nombre, 9001 AS no_habitacion,
           'Doble' AS tipo, 80.00 AS precio, 2 AS capacidad,
           'Dos camas individuales, baño privado y vista al jardín.' AS descripcion,
           0 AS mantenimiento
    UNION ALL SELECT 'Habitación Matrimonial Superior', 9002, 'Matrimonial', 95.00, 2,
           'Cama matrimonial, aire acondicionado y baño privado.', 0
    UNION ALL SELECT 'Suite Familiar', 9003, 'Suite', 150.00, 3,
           'Sala de estar, cama king y espacio para una cama adicional.', 0
    UNION ALL SELECT 'Habitación Doble Ejecutiva', 9004, 'Doble', 80.00, 2,
           'Dos camas individuales, escritorio y conexión Wi-Fi.', 0
    UNION ALL SELECT 'Matrimonial con Balcón', 9005, 'Matrimonial', 95.00, 2,
           'Cama matrimonial y balcón privado con vista al patio.', 0
    UNION ALL SELECT 'Deluxe Vista al Jardín', 9006, 'Deluxe', 120.00, 3,
           'Habitación amplia con sofá cama y vista al jardín.', 0
    UNION ALL SELECT 'Habitación Doble Económica', 9007, 'Doble', 80.00, 2,
           'Dos camas individuales, televisión y baño privado.', 0
    UNION ALL SELECT 'Deluxe Familiar', 9008, 'Deluxe', 120.00, 3,
           'Cama queen, sofá cama y espacio para tres huéspedes.', 0
    UNION ALL SELECT 'Suite Ejecutiva', 9009, 'Deluxe', 120.00, 3,
           'Área de descanso, escritorio y servicio a la habitación.', 0
    UNION ALL SELECT 'Habitación Doble Colonial', 9010, 'Doble', 80.00, 2,
           'Dos camas individuales y decoración de estilo colonial.', 0
    UNION ALL SELECT 'Matrimonial Estándar', 9011, 'Matrimonial', 95.00, 2,
           'Cama matrimonial, clóset y baño privado con ducha.', 0
    UNION ALL SELECT 'Matrimonial Superior con Terraza', 9012, 'Matrimonial', 95.00, 2,
           'Cama matrimonial y terraza privada.', 0
    UNION ALL SELECT 'Deluxe con Sofá Cama', 9013, 'Deluxe', 120.00, 3,
           'Cama queen, sofá cama y minibar.', 0
    UNION ALL SELECT 'Suite Presidencial', 9014, 'Presidencial', 180.00, 4,
           'Sala independiente, cama king y capacidad para cuatro huéspedes.', 0
    UNION ALL SELECT 'Habitación Individual', 9015, 'Simple', 55.00, 1,
           'Cama individual, escritorio y baño privado.', 0
    UNION ALL SELECT 'Suite Familiar con Sala', 9016, 'Suite', 150.00, 3,
           'Dormitorio privado y sala de estar para tres huéspedes.', 0
    UNION ALL SELECT 'Suite en Mantenimiento', 9017, 'Suite', 150.00, 3,
           'Suite amplia temporalmente fuera de servicio por mantenimiento.', 1
    UNION ALL SELECT 'Habitación Individual Ejecutiva', 9018, 'Simple', 55.00, 1,
           'Cama individual, escritorio de trabajo y Wi-Fi.', 0
    UNION ALL SELECT 'Habitación Doble con Vista al Patio', 9019, 'Doble', 80.00, 2,
           'Dos camas individuales y vista al patio interior.', 0
    UNION ALL SELECT 'Suite Presidencial Familiar', 9020, 'Presidencial', 180.00, 4,
           'Sala de estar independiente y capacidad para cuatro huéspedes.', 0
) AS datos
WHERE NOT EXISTS (
    SELECT 1
    FROM registro_habitacion h
    WHERE h.no_habitacion = datos.no_habitacion
);

-- Renombra las habitaciones insertadas por versiones anteriores del script.
UPDATE registro_habitacion
SET nombre = CASE no_habitacion
        WHEN 9001 THEN 'Habitación Doble Jardín'
        WHEN 9002 THEN 'Habitación Matrimonial Superior'
        WHEN 9003 THEN 'Suite Familiar'
        WHEN 9004 THEN 'Habitación Doble Ejecutiva'
        WHEN 9005 THEN 'Matrimonial con Balcón'
        WHEN 9006 THEN 'Deluxe Vista al Jardín'
        WHEN 9007 THEN 'Habitación Doble Económica'
        WHEN 9008 THEN 'Deluxe Familiar'
        WHEN 9009 THEN 'Suite Ejecutiva'
        WHEN 9010 THEN 'Habitación Doble Colonial'
        WHEN 9011 THEN 'Matrimonial Estándar'
        WHEN 9012 THEN 'Matrimonial Superior con Terraza'
        WHEN 9013 THEN 'Deluxe con Sofá Cama'
        WHEN 9014 THEN 'Suite Presidencial'
        WHEN 9015 THEN 'Habitación Individual'
        WHEN 9016 THEN 'Suite Familiar con Sala'
        WHEN 9017 THEN 'Suite en Mantenimiento'
        WHEN 9018 THEN 'Habitación Individual Ejecutiva'
        WHEN 9019 THEN 'Habitación Doble con Vista al Patio'
        WHEN 9020 THEN 'Suite Presidencial Familiar'
    END,
    descripcion = CASE no_habitacion
        WHEN 9001 THEN 'Dos camas individuales, baño privado y vista al jardín.'
        WHEN 9002 THEN 'Cama matrimonial, aire acondicionado y baño privado.'
        WHEN 9003 THEN 'Sala de estar, cama king y espacio para una cama adicional.'
        WHEN 9004 THEN 'Dos camas individuales, escritorio y conexión Wi-Fi.'
        WHEN 9005 THEN 'Cama matrimonial y balcón privado con vista al patio.'
        WHEN 9006 THEN 'Habitación amplia con sofá cama y vista al jardín.'
        WHEN 9007 THEN 'Dos camas individuales, televisión y baño privado.'
        WHEN 9008 THEN 'Cama queen, sofá cama y espacio para tres huéspedes.'
        WHEN 9009 THEN 'Área de descanso, escritorio y servicio a la habitación.'
        WHEN 9010 THEN 'Dos camas individuales y decoración de estilo colonial.'
        WHEN 9011 THEN 'Cama matrimonial, clóset y baño privado con ducha.'
        WHEN 9012 THEN 'Cama matrimonial y terraza privada.'
        WHEN 9013 THEN 'Cama queen, sofá cama y minibar.'
        WHEN 9014 THEN 'Sala independiente, cama king y capacidad para cuatro huéspedes.'
        WHEN 9015 THEN 'Cama individual, escritorio y baño privado.'
        WHEN 9016 THEN 'Dormitorio privado y sala de estar para tres huéspedes.'
        WHEN 9017 THEN 'Suite amplia temporalmente fuera de servicio por mantenimiento.'
        WHEN 9018 THEN 'Cama individual, escritorio de trabajo y Wi-Fi.'
        WHEN 9019 THEN 'Dos camas individuales y vista al patio interior.'
        WHEN 9020 THEN 'Sala de estar independiente y capacidad para cuatro huéspedes.'
    END
WHERE no_habitacion BETWEEN 9001 AND 9020;

-- Actualiza los datos visibles de las reservas creadas por la version anterior.
-- Conserva sus IDs y relaciones con pagos/tareas, pero reemplaza nombres y
-- documentos genéricos por datos ficticios con aspecto realista.
UPDATE Reserva r
JOIN (
    SELECT 'TEST-PEND-SIN-PAGO-01' AS identificacion, 'SIM-2026-0001' AS nuevo_id,
           'María Fernanda López' AS cliente, '+505 8888-4101' AS contacto
    UNION ALL SELECT 'TEST-PEND-PARCIAL-02', 'SIM-2026-0002', 'Carlos Alberto Ruiz', '+505 8888-4102'
    UNION ALL SELECT 'TEST-PEND-PAGADA-03', 'SIM-2026-0003', 'Ana Sofía Martínez', '+505 8888-4103'
    UNION ALL SELECT 'TEST-CHECKIN-HOY-04', 'SIM-2026-0004', 'José Manuel Gutiérrez', '+505 8888-4104'
    UNION ALL SELECT 'TEST-LLEGADA-PROXIMA-05', 'SIM-2026-0005', 'Laura Isabel Pineda', '+505 8888-4105'
    UNION ALL SELECT 'TEST-EN-CURSO-PARCIAL-06', 'SIM-2026-0006', 'Roberto Antonio Rivas', '+505 8888-4106'
    UNION ALL SELECT 'TEST-SALIDA-PAGADA-07', 'SIM-2026-0007', 'Gabriela Elena Morales', '+505 8888-4107'
    UNION ALL SELECT 'TEST-SALIDA-FORZADA-08', 'SIM-2026-0008', 'Francisco Javier Castillo', '+505 8888-4108'
    UNION ALL SELECT 'TEST-OVERSTAY-09', 'SIM-2026-0009', 'Claudia Beatriz Herrera', '+505 8888-4109'
    UNION ALL SELECT 'TEST-FINALIZADA-LIMPIEZA-10', 'SIM-2026-0010', 'Miguel Ángel Torres', '+505 8888-4110'
    UNION ALL SELECT 'TEST-CANCELADA-11', 'SIM-2026-0011', 'Patricia del Carmen Espinoza', '+505 8888-4111'
    UNION ALL SELECT 'TEST-CANCELAR-12', 'SIM-2026-0012', 'Daniela Alejandra Vargas', '+505 8888-4112'
    UNION ALL SELECT 'TEST-EDITAR-13', 'SIM-2026-0013', 'Ernesto Ramón Aguilar', '+505 8888-4113'
    UNION ALL SELECT 'TEST-CAPACIDAD-14', 'SIM-2026-0014', 'Valeria Fernanda Mendoza', '+505 8888-4114'
    UNION ALL SELECT 'TEST-HISTORIAL-15', 'SIM-2026-0015', 'Ricardo Andrés Salazar', '+505 8888-4115'
    UNION ALL SELECT 'TEST-LIMPIEZA-DIARIA-16', 'SIM-2026-0016', 'Lucía Beatriz Alemán', '+505 8888-4116'
    UNION ALL SELECT 'TEST-RESERVA-LEJANA-17', 'SIM-2026-0017', 'Andrea Carolina Rocha', '+505 8888-4117'
) AS datos ON r.identificacion = datos.identificacion
SET r.identificacion = datos.nuevo_id,
    r.cliente = datos.cliente,
    r.contacto = datos.contacto;

-- Reservas para los principales escenarios de recepción y administración.
-- Cada habitación tiene un escenario separado para evitar solapamientos.
-- Los totales corresponden a precio por noche x noches.
INSERT INTO Reserva
    (cliente, identificacion, contacto, numero_huespedes, noches,
     fecha_entrada, fecha_salida, metodo_pago, total, monto_pagado, estado,
     habitacion_id, empleado_id, checkin_empleado_id, salida_empleado_id)
SELECT datos.cliente, datos.identificacion, datos.contacto,
       datos.numero_huespedes, datos.noches, datos.fecha_entrada,
       datos.fecha_salida, datos.metodo_pago, datos.total, datos.monto_pagado,
       datos.estado, h.id, recepcion.id,
       CASE WHEN datos.estado = 'Iniciada' THEN recepcion.id ELSE NULL END,
       CASE
           WHEN datos.estado IN ('Finalizada', 'Cancelada') THEN admin.id
           ELSE NULL
       END
FROM (
    SELECT 'María Fernanda López' AS cliente, 'SIM-2026-0001' AS identificacion,
           '+505 8888-4101' AS contacto, 2 AS numero_huespedes, 3 AS noches,
           DATE_ADD(CURDATE(), INTERVAL 7 DAY) AS fecha_entrada,
           DATE_ADD(CURDATE(), INTERVAL 10 DAY) AS fecha_salida,
           'Efectivo en Recepción' AS metodo_pago, 240.00 AS total,
           0.00 AS monto_pagado, 'Pendiente' AS estado, 9001 AS no_habitacion
    UNION ALL SELECT 'Carlos Alberto Ruiz', 'SIM-2026-0002', '+505 8888-4102',
           2, 2, DATE_ADD(CURDATE(), INTERVAL 11 DAY),
           DATE_ADD(CURDATE(), INTERVAL 13 DAY),
           'Tarjeta de Crédito / Débito', 190.00, 50.00, 'Pendiente', 9002
    UNION ALL SELECT 'Ana Sofía Martínez', 'SIM-2026-0003', '+505 8888-4103',
           3, 2, DATE_ADD(CURDATE(), INTERVAL 15 DAY),
           DATE_ADD(CURDATE(), INTERVAL 17 DAY),
           'Transferencia Bancaria', 300.00, 300.00, 'Pendiente', 9003
    UNION ALL SELECT 'José Manuel Gutiérrez', 'SIM-2026-0004', '+505 8888-4104',
           2, 2, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 2 DAY),
           'Efectivo en Recepción', 160.00, 0.00, 'Pendiente', 9004
    UNION ALL SELECT 'Laura Isabel Pineda', 'SIM-2026-0005', '+505 8888-4105',
           2, 2, DATE_ADD(CURDATE(), INTERVAL 1 DAY),
           DATE_ADD(CURDATE(), INTERVAL 3 DAY),
           'Tarjeta de Crédito / Débito', 190.00, 0.00, 'Pendiente', 9005
    UNION ALL SELECT 'Roberto Antonio Rivas', 'SIM-2026-0006', '+505 8888-4106',
           3, 3, DATE_SUB(CURDATE(), INTERVAL 1 DAY),
           DATE_ADD(CURDATE(), INTERVAL 2 DAY),
           'Tarjeta de Crédito / Débito', 360.00, 120.00, 'Iniciada', 9006
    UNION ALL SELECT 'Gabriela Elena Morales', 'SIM-2026-0007', '+505 8888-4107',
           2, 2, DATE_SUB(CURDATE(), INTERVAL 1 DAY),
           DATE_ADD(CURDATE(), INTERVAL 1 DAY),
           'Efectivo en Recepción', 160.00, 160.00, 'Iniciada', 9007
    UNION ALL SELECT 'Francisco Javier Castillo', 'SIM-2026-0008', '+505 8888-4108',
           3, 3, DATE_SUB(CURDATE(), INTERVAL 1 DAY),
           DATE_ADD(CURDATE(), INTERVAL 2 DAY),
           'Transferencia Bancaria', 360.00, 80.00, 'Iniciada', 9008
    UNION ALL SELECT 'Claudia Beatriz Herrera', 'SIM-2026-0009', '+505 8888-4109',
           2, 5, DATE_SUB(CURDATE(), INTERVAL 5 DAY),
           DATE_SUB(CURDATE(), INTERVAL 2 DAY),
           'Efectivo en Recepción', 600.00, 0.00, 'Iniciada', 9009
    UNION ALL SELECT 'Miguel Ángel Torres', 'SIM-2026-0010', '+505 8888-4110',
           2, 2, DATE_SUB(CURDATE(), INTERVAL 3 DAY),
           DATE_SUB(CURDATE(), INTERVAL 1 DAY),
           'Tarjeta de Crédito / Débito', 160.00, 160.00, 'Finalizada', 9010
    UNION ALL SELECT 'Patricia del Carmen Espinoza', 'SIM-2026-0011', '+505 8888-4111',
           2, 2, DATE_ADD(CURDATE(), INTERVAL 20 DAY),
           DATE_ADD(CURDATE(), INTERVAL 22 DAY),
           'Efectivo en Recepción', 190.00, 0.00, 'Cancelada', 9011
    UNION ALL SELECT 'Daniela Alejandra Vargas', 'SIM-2026-0012', '+505 8888-4112',
           2, 2, DATE_ADD(CURDATE(), INTERVAL 30 DAY),
           DATE_ADD(CURDATE(), INTERVAL 32 DAY),
           'Efectivo en Recepción', 190.00, 0.00, 'Pendiente', 9012
    UNION ALL SELECT 'Ernesto Ramón Aguilar', 'SIM-2026-0013', '+505 8888-4113',
           3, 3, DATE_ADD(CURDATE(), INTERVAL 35 DAY),
           DATE_ADD(CURDATE(), INTERVAL 38 DAY),
           'Tarjeta de Crédito / Débito', 360.00, 0.00, 'Pendiente', 9013
    UNION ALL SELECT 'Valeria Fernanda Mendoza', 'SIM-2026-0014', '+505 8888-4114',
           4, 2, DATE_ADD(CURDATE(), INTERVAL 40 DAY),
           DATE_ADD(CURDATE(), INTERVAL 42 DAY),
           'Transferencia Bancaria', 360.00, 0.00, 'Pendiente', 9014
    UNION ALL SELECT 'Ricardo Andrés Salazar', 'SIM-2026-0015', '+505 8888-4115',
           1, 2, DATE_SUB(CURDATE(), INTERVAL 30 DAY),
           DATE_SUB(CURDATE(), INTERVAL 28 DAY),
           'Transferencia Bancaria', 110.00, 110.00, 'Finalizada', 9015
    UNION ALL SELECT 'Lucía Beatriz Alemán', 'SIM-2026-0016', '+505 8888-4116',
           2, 4, DATE_SUB(CURDATE(), INTERVAL 1 DAY),
           DATE_ADD(CURDATE(), INTERVAL 3 DAY),
           'Efectivo en Recepción', 600.00, 0.00, 'Iniciada', 9016
    UNION ALL SELECT 'Andrea Carolina Rocha', 'SIM-2026-0017', '+505 8888-4117',
           2, 2, DATE_ADD(CURDATE(), INTERVAL 50 DAY),
           DATE_ADD(CURDATE(), INTERVAL 52 DAY),
           'Tarjeta de Crédito / Débito', 160.00, 0.00, 'Pendiente', 9019
) AS datos
JOIN registro_habitacion h ON h.no_habitacion = datos.no_habitacion
JOIN Usuario recepcion ON recepcion.username = 'recepcion'
JOIN Usuario admin ON admin.username = 'admin'
WHERE NOT EXISTS (
    SELECT 1
    FROM Reserva r
    WHERE r.identificacion = datos.identificacion
);

-- Pagos previos coherentes con el saldo que se muestra en las reservas.
INSERT INTO Pago (reserva_id, monto, metodo_pago, empleado_id)
SELECT r.id, datos.monto, datos.metodo_pago, recepcion.id
FROM (
    SELECT 'SIM-2026-0002' AS identificacion, 50.00 AS monto,
           'Tarjeta de Crédito / Débito' AS metodo_pago
    UNION ALL SELECT 'SIM-2026-0003', 300.00, 'Transferencia Bancaria'
    UNION ALL SELECT 'SIM-2026-0006', 120.00, 'Tarjeta de Crédito / Débito'
    UNION ALL SELECT 'SIM-2026-0007', 160.00, 'Efectivo en Recepción'
    UNION ALL SELECT 'SIM-2026-0008', 80.00, 'Transferencia Bancaria'
    UNION ALL SELECT 'SIM-2026-0010', 160.00, 'Tarjeta de Crédito / Débito'
    UNION ALL SELECT 'SIM-2026-0015', 110.00, 'Transferencia Bancaria'
) AS datos
JOIN Reserva r ON r.identificacion = datos.identificacion
JOIN Usuario recepcion ON recepcion.username = 'recepcion'
WHERE NOT EXISTS (
    SELECT 1
    FROM Pago p
    WHERE p.reserva_id = r.id
      AND p.monto = datos.monto
      AND p.metodo_pago = datos.metodo_pago
);

-- Limpieza de salida pendiente para que el catálogo marque la habitación 9010
-- como no disponible hasta finalizar el servicio.
INSERT INTO TareaHabitacion
    (habitacion_id, reserva_id, tipo, turno, fecha_programada, estado)
SELECT h.id, r.id, 'Limpieza de salida', 'Salida', CURDATE(), 'Pendiente'
FROM Reserva r
JOIN registro_habitacion h ON h.id = r.habitacion_id
WHERE r.identificacion = 'SIM-2026-0010'
  AND NOT EXISTS (
      SELECT 1
      FROM TareaHabitacion t
      WHERE t.reserva_id = r.id
        AND t.tipo = 'Limpieza de salida'
  );

-- Ejemplo de limpieza diaria completada con tiempo y empleado registrados.
-- El panel generará automáticamente los otros turnos de la estancia activa.
INSERT INTO TareaHabitacion
    (habitacion_id, reserva_id, tipo, turno, fecha_programada, estado,
     iniciada_en, finalizada_en, iniciada_por, finalizada_por)
SELECT h.id, r.id, 'Limpieza diaria', 'Mañana', CURDATE(), 'Completada',
       DATE_SUB(NOW(), INTERVAL 55 MINUTE),
       DATE_SUB(NOW(), INTERVAL 25 MINUTE), recepcion.id, recepcion.id
FROM Reserva r
JOIN registro_habitacion h ON h.id = r.habitacion_id
JOIN Usuario recepcion ON recepcion.username = 'recepcion'
WHERE r.identificacion = 'SIM-2026-0016'
  AND NOT EXISTS (
      SELECT 1
      FROM TareaHabitacion t
      WHERE t.reserva_id = r.id
        AND t.tipo = 'Limpieza diaria'
        AND t.fecha_programada = CURDATE()
        AND t.turno = 'Mañana'
  );

-- Tarea técnica iniciada para la habitación 9017, que se inserta en
-- mantenimiento. Permite probar su finalización desde el panel (solo admin).
INSERT INTO TareaHabitacion
    (habitacion_id, tipo, turno, fecha_programada, estado,
     iniciada_en, iniciada_por)
SELECT h.id, 'Mantenimiento técnico', 'Mantenimiento', CURDATE(), 'En proceso',
       DATE_SUB(NOW(), INTERVAL 4 HOUR), admin.id
FROM registro_habitacion h
JOIN Usuario admin ON admin.username = 'admin'
WHERE h.no_habitacion = 9017
  AND NOT EXISTS (
      SELECT 1
      FROM TareaHabitacion t
      WHERE t.habitacion_id = h.id
        AND t.tipo = 'Mantenimiento técnico'
  );

COMMIT;

-- Resumen para confirmar que los datos de prueba quedaron cargados.
SELECT 'Habitaciones de simulación' AS dato, COUNT(*) AS cantidad
FROM registro_habitacion
WHERE no_habitacion BETWEEN 9001 AND 9020
UNION ALL
SELECT 'Reservas de simulación', COUNT(*)
FROM Reserva
WHERE identificacion LIKE 'SIM-2026-%'
UNION ALL
SELECT 'Pagos de simulación', COUNT(*)
FROM Pago p
JOIN Reserva r ON r.id = p.reserva_id
WHERE r.identificacion LIKE 'SIM-2026-%'
UNION ALL
SELECT 'Tareas de habitación de simulación', COUNT(*)
FROM TareaHabitacion t
LEFT JOIN Reserva r ON r.id = t.reserva_id
LEFT JOIN registro_habitacion h ON h.id = t.habitacion_id
WHERE r.identificacion LIKE 'SIM-2026-%'
   OR h.no_habitacion = 9017;
