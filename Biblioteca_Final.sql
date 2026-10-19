CREATE DATABASE biblioteca_universidad;

USE biblioteca_universidad;


-- Tabla libros

CREATE TABLE libros (
    isbn VARCHAR(20) PRIMARY KEY,
    titulo VARCHAR(200),
    editorial VARCHAR(150),
    año INT,
    descripcion VARCHAR(500)
);


-- Tabla libro_autor

CREATE TABLE libro_autor (
    isbn VARCHAR(20),
    autor VARCHAR(150),

    PRIMARY KEY (isbn, autor),

    FOREIGN KEY (isbn)
    REFERENCES libros(isbn)
    );



-- Tabla libro_categoria

CREATE TABLE libro_categoria (
    isbn VARCHAR(20),
    categoria VARCHAR(100),

    PRIMARY KEY (isbn, categoria),

    FOREIGN KEY (isbn)
    REFERENCES libros(isbn)
);


-- Tabla ejemplares

CREATE TABLE ejemplares (
    id_ejemplar INT AUTO_INCREMENT PRIMARY KEY,
    isbn VARCHAR(20),
    sala VARCHAR(50),
    estante VARCHAR(50),
    estado VARCHAR(30),

    FOREIGN KEY (isbn)
    REFERENCES libros(isbn)
);


-- Tabla usuarios

CREATE TABLE usuarios (
    codigo VARCHAR(20) PRIMARY KEY,
    identificacion VARCHAR(20),
    nombres VARCHAR(150),
    correo VARCHAR(150),
    carrera VARCHAR(150),
    estado VARCHAR(30),
    rol VARCHAR(30)
);


-- Tabla usuario_admin

CREATE TABLE usuario_admin (
    codigo VARCHAR(20) PRIMARY KEY,

    FOREIGN KEY (codigo)
    REFERENCES usuarios(codigo)
);


-- Tabla prestamos

CREATE TABLE prestamos (
    id_ejemplar INT,
    codigo_usuario VARCHAR(20),
    fec_prestamo DATE,
    fec_vencimiento DATE,
    fec_devolucion DATE,
    observaciones VARCHAR(300),
    estado VARCHAR(30),
    sancion DECIMAL(10,2),

    PRIMARY KEY (
        id_ejemplar,
        codigo_usuario,
        fec_prestamo
    ),

    FOREIGN KEY (id_ejemplar)
    REFERENCES ejemplares(id_ejemplar),

    FOREIGN KEY (codigo_usuario)
    REFERENCES usuarios(codigo)
);


-- Insertar libros

INSERT INTO libros
(isbn, titulo, editorial, año, descripcion)
VALUES
(
    '9780132350884',
    'Clean Code',
    'Prentice Hall',
    2008,
    'Libro sobre buenas practicas para escribir codigo limpio y mantenible.'
),
(
    '9780133970777',
    'Fundamentals of Database Systems',
    'Pearson',
    2015,
    'Libro sobre diseño, modelamiento y administracion de bases de datos.'
),
(
    '9780262033848',
    'Introduction to Algorithms',
    'MIT Press',
    2009,
    'Libro sobre algoritmos, estructuras de datos y analisis computacional.'
),
(
    '9780131103627',
    'The C Programming Language',
    'Prentice Hall',
    1988,
    'Libro introductorio al lenguaje de programacion C.'
),
(
    '9781449373320',
    'Designing Data Intensive Applications',
    'OReilly Media',
    2017,
    'Libro sobre sistemas distribuidos y aplicaciones orientadas a datos.'
),
(
    '9780307474728',
    'Cien años de soledad',
    'Vintage Espanol',
    1967,
    'Novela de Gabriel Garcia Marquez sobre la familia Buendia y Macondo.'
),
(
    '9780451524935',
    '1984',
    'Signet Classics',
    1949,
    'Novela distopica sobre vigilancia, poder y control social.'
),
(
    '9780141439518',
    'Orgullo y prejuicio',
    'Penguin Classics',
    1813,
    'Novela clasica de romance y sociedad escrita por Jane Austen.'
),
(
    '9780547928227',
    'El Hobbit',
    'Mariner Books',
    1937,
    'Novela fantastica sobre el viaje de Bilbo Bolson.'
),
(
    '9780590353427',
    'Harry Potter y la piedra filosofal',
    'Scholastic',
    1997,
    'Novela fantastica sobre el inicio de Harry Potter en Hogwarts.'
),
(
    '9780062693662',
    'Asesinato en el Orient Express',
    'HarperCollins',
    1934,
    'Novela de misterio protagonizada por el detective Hercule Poirot.'
),
(
    '9780441172719',
    'Dune',
    'Ace Books',
    1965,
    'Novela de ciencia ficcion ambientada en el planeta Arrakis.'
),
(
    '9780156012195',
    'El Principito',
    'Mariner Books',
    1943,
    'Historia sobre amistad, humanidad y el sentido de la vida.'
),
(
    '9780062315007',
    'El Alquimista',
    'HarperOne',
    1988,
    'Novela sobre el viaje de un joven en busca de su destino.'
),
(
    '9780060934347',
    'Don Quijote de la Mancha',
    'HarperCollins',
    1605,
    'Novela clasica sobre las aventuras de Don Quijote y Sancho Panza.'
);


-- Insertar relaciones libro_autor

INSERT INTO libro_autor
(isbn, autor)
VALUES
('9780132350884', 'Robert C. Martin'),

('9780133970777', 'Ramez Elmasri'),
('9780133970777', 'Shamkant B. Navathe'),

('9780262033848', 'Thomas H. Cormen'),
('9780262033848', 'Charles E. Leiserson'),
('9780262033848', 'Ronald L. Rivest'),
('9780262033848', 'Clifford Stein'),

('9780131103627', 'Brian W. Kernighan'),
('9780131103627', 'Dennis M. Ritchie'),

('9781449373320', 'Martin Kleppmann'),

('9780307474728', 'Gabriel Garcia Marquez'),

('9780451524935', 'George Orwell'),

('9780141439518', 'Jane Austen'),

('9780547928227', 'J. R. R. Tolkien'),

('9780590353427', 'J. K. Rowling'),

('9780062693662', 'Agatha Christie'),

('9780441172719', 'Frank Herbert'),

('9780156012195', 'Antoine de Saint-Exupery'),

('9780062315007', 'Paulo Coelho'),

('9780060934347', 'Miguel de Cervantes');



-- Insertar relaciones libro_categoria

INSERT INTO libro_categoria
(isbn, categoria)
VALUES
('9780132350884', 'Programacion'),
('9780132350884', 'Ingenieria de Software'),

('9780133970777', 'Bases de Datos'),
('9780133970777', 'Informatica'),

('9780262033848', 'Algoritmos'),
('9780262033848', 'Ciencias de la Computacion'),

('9780131103627', 'Programacion'),

('9781449373320', 'Bases de Datos'),
('9781449373320', 'Sistemas Distribuidos'),

('9780307474728', 'Ficcion'),
('9780307474728', 'Realismo Magico'),

('9780451524935', 'Ficcion'),
('9780451524935', 'Distopia'),

('9780141439518', 'Ficcion'),
('9780141439518', 'Romance'),
('9780141439518', 'Clasico'),

('9780547928227', 'Fantasia'),
('9780547928227', 'Aventura'),

('9780590353427', 'Fantasia'),
('9780590353427', 'Aventura'),

('9780062693662', 'Misterio'),
('9780062693662', 'Novela Policiaca'),

('9780441172719', 'Ciencia Ficcion'),
('9780441172719', 'Aventura'),

('9780156012195', 'Ficcion'),
('9780156012195', 'Infantil'),

('9780062315007', 'Ficcion'),
('9780062315007', 'Aventura'),

('9780060934347', 'Clasico'),
('9780060934347', 'Ficcion'),
('9780060934347', 'Aventura');



-- Insertar ejemplares

INSERT INTO ejemplares
(isbn, sala, estante, estado)
VALUES

-- Clean Code
('9780132350884', 'Sala 1', 'A1', 'Disponible'),
('9780132350884', 'Sala 1', 'A1', 'Prestado'),

-- Fundamentals of Database Systems
('9780133970777', 'Sala 1', 'A2', 'Disponible'),
('9780133970777', 'Sala 1', 'A2', 'Prestado'),

-- Introduction to Algorithms
('9780262033848', 'Sala 1', 'A3', 'Disponible'),
('9780262033848', 'Sala 1', 'A3', 'Disponible'),

-- The C Programming Language
('9780131103627', 'Sala 1', 'A4', 'Disponible'),

-- Designing Data Intensive Applications
('9781449373320', 'Sala 1', 'A5', 'Disponible'),

-- Cien años de soledad
('9780307474728', 'Sala 2', 'B1', 'Prestado'),
('9780307474728', 'Sala 2', 'B1', 'Disponible'),

-- 1984
('9780451524935', 'Sala 2', 'B2', 'Disponible'),
('9780451524935', 'Sala 2', 'B2', 'Disponible'),

-- Orgullo y prejuicio
('9780141439518', 'Sala 2', 'B3', 'Disponible'),

-- El Hobbit
('9780547928227', 'Sala 2', 'B4', 'Prestado'),
('9780547928227', 'Sala 2', 'B4', 'Disponible'),

-- Harry Potter
('9780590353427', 'Sala 2', 'B5', 'Disponible'),
('9780590353427', 'Sala 2', 'B5', 'Disponible'),

-- Asesinato en el Orient Express
('9780062693662', 'Sala 3', 'C1', 'Disponible'),

-- Dune
('9780441172719', 'Sala 3', 'C2', 'Prestado'),
('9780441172719', 'Sala 3', 'C2', 'Disponible'),

-- El Principito
('9780156012195', 'Sala 3', 'C3', 'Disponible'),

-- El Alquimista
('9780062315007', 'Sala 3', 'C4', 'Disponible'),

-- Don Quijote
('9780060934347', 'Sala 3', 'C5', 'Disponible'),
('9780060934347', 'Sala 3', 'C5', 'Perdido');



-- Insertar usuarios

INSERT INTO usuarios
(codigo, identificacion, nombres, correo, carrera, estado, rol)
VALUES
(
    'U001',
    '1000000001',
    'Maria Fernandez',
    'maria@correo.com',
    'Ingenieria Industrial',
    'Activo',
    'Estudiante'
),
(
    'A001',
    '72000002',
    'Administrador Biblioteca',
    'admin@biblioteca.com',
    NULL,
    'Activo',
    'Administrador'
);


-- Insertar usuario administrador

INSERT INTO usuario_admin
(codigo)
VALUES
('A001');


-- Insertar prestamos

INSERT INTO prestamos
(
    id_ejemplar,
    codigo_usuario,
    fec_prestamo,
    fec_vencimiento,
    fec_devolucion,
    observaciones,
    estado,
    sancion
)
VALUES
(
    2,
    'U001',
    '2026-10-01',
    '2026-10-15',
    NULL,
    NULL,
    'Activo',
    0
);
use biblioteca_universidad;
ALTER TABLE usuarios
ADD CONSTRAINT chk_estado_usuario 
CHECK (estado IN ('activo', 'bloqueado'));
INSERT INTO usuarios
(codigo, identificacion, nombres, correo, carrera, estado, rol)
VALUES
    ('U005', '1000000005', 'Valeria Sofia Rojas', 'valeria.rojas@correo.com', 'Ingeniería de Sistemas', 'activo', 'Estudiante'),
    ('U006', '1000000006', 'Lucas David Navarro', 'lucas.navarro@correo.com', 'Ingeniería Industrial', 'activo', 'Estudiante'),
    ('U007', '1000000007', 'Camila Andrea Torres', 'camila.torres@correo.com', 'Derecho', 'activo', 'Estudiante'),
    ('U008', '1000000008', 'Esteban Jose Morales', 'esteban.morales@correo.com', 'Administración de Empresas', 'bloqueado', 'Estudiante'),
    ('U009', '1000000009', 'Mariana Alejandra Silva', 'mariana.silva@correo.com', 'Medicina', 'activo', 'Estudiante'),
    ('U010', '1000000010', 'Joaquin Alberto Castro', 'joaquin.castro@correo.com', 'Arquitectura', 'activo', 'Estudiante'),
    ('U011', '1000000011', 'Lucia Valentina Blanco', 'lucia.blanco@correo.com', 'Diseño Gráfico', 'activo', 'Estudiante'),
    ('U012', '1000000012', 'Emiliano Jose Paternina', 'emiliano.paternina@correo.com', 'Economía', 'activo', 'Estudiante'),
    ('D003', '80000003', 'Dr. Roberto Carlos Hinojosa', 'roberto.hinojosa@uninorte.edu.co', NULL, 'activo', 'Docente'),
    ('D004', '80000004', 'Dra. Carmen Rosa de la Espriella', 'carmen.delaespriella@uninorte.edu.co', NULL, 'activo', 'Docente'),
    ('D005', '80000005', 'Ing. Fernando Enrique Orozco', 'fernando.orozco@uninorte.edu.co', NULL, 'activo', 'Docente'),
    ('D006', '80000006', 'Dra. Beatriz Elena Sotomayor', 'beatriz.sotomayor@uninorte.edu.co', NULL, 'bloqueado', 'Docente'),
    ('B001', '90000001', 'Claudia Patricia Meza', 'claudia.meza@biblioteca.com', NULL, 'activo', 'Bibliotecario'),
    ('B002', '90000002', 'Javier Enrique Cardenas', 'javier.cardenas@biblioteca.com', NULL, 'activo', 'Bibliotecario'),
    ('A002', '72000003', 'Super Admin Soporte BD', 'soporte.admin@biblioteca.com', NULL, 'activo', 'Administrador');
SET SQL_SAFE_UPDATES = 0;
UPDATE ejemplares 
SET estado = 'Disponible';
select * from usuarios;
UPDATE usuarios  
SET rol = 'Administrador'
where rol = 'Bibliotecario';
select * from usuarios;