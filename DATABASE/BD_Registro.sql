CREATE DATABASE IF NOT EXISTS db_sistema_reserva;
USE db_sistema_reserva;

CREATE TABLE Usuario (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    passwrd VARCHAR(255) NOT NULL,
    rol ENUM('user', 'administrador') NOT NULL,
    nombre_completo VARCHAR(150) NOT NULL,
    numero_identificacion VARCHAR(100) NOT NULL UNIQUE,
    correo_electronico VARCHAR(255) NOT NULL UNIQUE,
    numero_telefono VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE registro_habitacion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100),
    no_habitacion INT NOT NULL UNIQUE,
    tipo ENUM('Simple', 'Doble', 'Matrimonial', 'Suite', 'Deluxe', 'Presidencial') DEFAULT 'Simple',
    precio DECIMAL(10,2),
    capacidad VARCHAR(50),
    descripcion VARCHAR(255),
    imagen VARCHAR(500)
);

CREATE TABLE Reserva (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente VARCHAR(100),
    identificacion VARCHAR(100) NOT NULL,
    contacto VARCHAR(100) NOT NULL,
    correo_electronico VARCHAR(255),
    noches INT NOT NULL,
    fecha_entrada DATE NOT NULL,
    fecha_salida DATE NOT NULL,
    metodo_pago ENUM('Tarjeta de Crédito / Débito', 'Efectivo en Recepción', 'Transferencia Bancaria') NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    usuario_id INT,
    habitacion_id INT,
    FOREIGN KEY (usuario_id) REFERENCES Usuario(id),
    FOREIGN KEY (habitacion_id) REFERENCES registro_habitacion(id)
);

CREATE TABLE estado (
    id_estado INT AUTO_INCREMENT PRIMARY KEY,
    habitacion_id INT NOT NULL,
    estatus ENUM('Disponible', 'Ocupado') NOT NULL,
    UNIQUE (habitacion_id),
    FOREIGN KEY (habitacion_id) REFERENCES registro_habitacion(id) ON DELETE CASCADE
);

-- Inserciones de datos de prueba
INSERT INTO Usuario
(id, username, passwrd, rol, nombre_completo, numero_identificacion, correo_electronico, numero_telefono) VALUES
(1, 'user', '1234', 'user', 'Usuario Demo', 'DEMO-0001', 'demo@example.com', '0123-4567'),
(2, 'admin', '1234', 'administrador', 'Administrador', 'DEMO-0002', 'admin@example.com', '1234-5678');

SELECT * FROM Usuario;

INSERT INTO registro_habitacion (id, nombre, no_habitacion, tipo, precio, capacidad, descripcion) VALUES
(1, 'Suite Presidencial Vista al Mar', 101, 'Suite', 150.00, '2 personas', 'Incluye cama King Size, jacuzzi privado, vista panorámica al mar y servicio a la habitación 24/7.');

SELECT * FROM registro_habitacion;

-- Inserción inicial de estado para la habitación creada
INSERT INTO estado (habitacion_id, estatus) VALUES (1, 'Disponible');

SELECT * FROM estado;