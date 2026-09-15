create database db_sistema_reserva;
use db_sistema_reserva;

create table Usuario(
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    passwrd VARCHAR(255) NOT NULL,
    rol ENUM('user', 'administrador') NOT NULL
);

CREATE TABLE Reserva (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente varchar(100),
    identificacion varchar(100) not null unique,
    noches int
);

CREATE TABLE registro_habitacion (
	id int primary key,
    nombre varchar(100),
    no_habitacion int,
    tipo enum('Simple', 'Doble', 'Matrimonial', 'Suite', 'Deluxe', 'Presencial') default 'Simple',
    precio decimal(10,5),
    capacidad varchar(50),
    descripcion varchar(255)
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

INSERT INTO Usuario (id, username, passwrd, rol) VALUES
(1, 'user', 1234, 'user'),
(2, 'admin', 1234, 'administrador');
select * from Usuario;

INSERT INTO registro_habitacion (id, nombre, no_habitacion, tipo, precio, capacidad, descripcion) VALUES
(1, 'Suite Presidencial Vista al Mar', 101, 'Suite', 150.00, 2, 'Incluye cama King Size, jacuzzi privado, vista panorámica al mar y servicio a la habitación 24/7.');
select * from registro_habitacion;