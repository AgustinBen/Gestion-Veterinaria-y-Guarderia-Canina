# Spec: interfaz transversal

## Estado

Decisiones aprobadas para la mejora visual solicitada el 2026-10-31.

## Alcance

Cambios de presentación compartidos entre `core`, `identidad`, `padron`,
`guarderia`, `cobros` y el resumen visual de `panel`. No alteran rutas,
permisos, datos ni reglas de negocio.

## Criterios de aceptación

- Los rótulos de sección mantienen el mismo estilo y una inclinación leve.
- La navegación lateral, inferior y su menú secundario usan un fondo ámbar suave.
- El nombre y rol del usuario se centran en el pie del menú lateral.
- Las barras de desplazamiento tienen estilo Huellitas y el desplazamiento suave
  respeta la preferencia de movimiento reducido del sistema.
- En Administración, Personal y Veterinario se muestran en dos columnas; queda
  un único botón Volver, junto a Crear cuenta.
- Dueños y mascotas muestra el rótulo “Padrón de clientes” y pagina las mascotas
  registradas en grupos de cinco.
- La barra superior de navegación comparte el fondo ámbar suave del menú.
- El resumen visual del Panel presenta las etiquetas Mensual y Anual una al lado
  de la otra.
- En Padrón se retiran los textos informativos solicitados y se conserva la
  navegación por página.
- Cobros muestra cinco clientes por página y no incluye los rótulos ni textos
  informativos señalados.
- La cuenta del cliente no muestra el enlace “Ver cuenta” ni el texto auxiliar
  del historial.
- El login y la marca de huellita tienen animaciones breves que respetan
  `prefers-reduced-motion`.
- La animación de ingreso al login es claramente perceptible y más lenta; las
  tarjetas de mascotas replican la composición visual de clientes de Cobros.
- El patrón de huellitas se prolonga visualmente por debajo del menú y de la
  barra superior sin perder el fondo ámbar suave ni repetir/cortar el patrón.
- Los selectores y el calendario de fechas usan controles propios con el estilo
  Huellitas, manteniendo teclado, estados accesibles y selección original.
- Nueva reserva se inicia desde el botón de Calendario; no aparece como enlace
  independiente en la navegación. La ruta y sus permisos se conservan.
- El patrón de huellitas también es claramente visible dentro del menú y del
  encabezado, alineado al fondo general para que continúe sin cortes.
- En Panel, Padrón y Cobros no se duplican subtítulos ni etiquetas de búsqueda;
  los campos mantienen nombres accesibles.
- El indicador circular de “Pendiente” en Deudores tiene un latido suave que
  respeta `prefers-reduced-motion`.
- La pantalla “Sin acceso” centra el título y el subrayado decorativo.
- Los selectores personalizados no ofrecen como opción seleccionable un texto
  de instrucción como “Seleccionar especie”; el placeholder queda solo como
  indicación visual mientras no haya valor elegido.
- La ilustración de la navegación lateral saluda al usuario autenticado por su
  nombre, sin consultar datos de Guardería.
- El contador de Deudores queda alineado al extremo derecho del menú y destaca
  con mayor tamaño y contraste, también en el menú secundario móvil.

## Fuera de alcance

Cambios de API, permisos, datos o reglas de negocio.
