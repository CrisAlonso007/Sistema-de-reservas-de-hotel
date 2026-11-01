-- Actualizacion segura para habilitar historial de pagos, devoluciones
-- y comprobantes en una base existente.
-- No elimina ni modifica los pagos, reservas o usuarios actuales.

USE db_sistema_reserva;

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
