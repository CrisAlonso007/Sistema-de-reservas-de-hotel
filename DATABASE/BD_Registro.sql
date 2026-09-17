create database db_sistema_reserva;
use db_sistema_reserva;

create table Usuario(
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    passwrd VARCHAR(255) NOT NULL,
    rol ENUM('user', 'administrador') NOT NULL,
    nombre_completo VARCHAR(150) NOT NULL,
    identificacion VARCHAR(50) NOT NULL UNIQUE,
    contacto VARCHAR(100) NOT NULL
);

CREATE TABLE registro_habitacion (
	id INT AUTO_INCREMENT PRIMARY KEY,
    nombre varchar(100),
    no_habitacion int NOT NULL UNIQUE,
    tipo enum('Simple', 'Doble', 'Matrimonial', 'Suite', 'Deluxe', 'Presencial') default 'Simple',
    precio decimal(10,5),
    capacidad varchar(50),
    descripcion varchar(255)
);

CREATE TABLE Reserva (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente varchar(100),
    identificacion varchar(100) not null,
    contacto varchar(100) not null,
    noches int not null,
    fecha_entrada DATE NOT NULL,
    fecha_salida DATE NOT NULL,
    metodo_pago ENUM('Tarjeta de Crédito / Débito', 'Efectivo en Recepción', 'Transferencia Bancaria') NOT NULL,
    total decimal(10,2) NOT NULL,
    usuario_id INT,
    habitacion_id INT,
    FOREIGN KEY (usuario_id) REFERENCES Usuario(id),
    FOREIGN KEY (habitacion_id) REFERENCES registro_habitacion(id)
);

-- CREATE TABLE Pago (
    -- id INT AUTO_INCREMENT PRIMARY KEY,
    -- reserva_id INT NOT NULL,
    -- monto DECIMAL(10,2) NOT NULL,
    -- metodo_pago ENUM('TARJETA', 'PAYPAL', 'TRANSFERENCIA', 'EFECTIVO') NOT NULL,
    -- estado ENUM('PENDIENTE', 'COMPLETADO', 'RECHAZADO', 'REEMBOLSADO') DEFAULT 'PENDIENTE',
    -- transaccion_id VARCHAR(100),
    -- fecha_pago TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- FOREIGN KEY (reserva_id) REFERENCES Reserva(id) ON DELETE CASCADE
-- );

INSERT INTO Usuario
(id, username, passwrd, rol, nombre_completo, identificacion, contacto) VALUES
(1, 'user', 1234, 'user', 'Usuario Demo', 'DEMO-0001', 'demo@example.com'),
(2, 'admin', 1234, 'administrador', 'Administrador', 'DEMO-0002', 'admin@example.com');
select * from Usuario;

INSERT INTO registro_habitacion (id, nombre, no_habitacion, tipo, precio, capacidad, descripcion) VALUES
(1, 'Suite Presidencial Vista al Mar', 101, 'Suite', 150.00, 2, 'Incluye cama King Size, jacuzzi privado, vista panorámica al mar y servicio a la habitación 24/7.');
select * from registro_habitacion;